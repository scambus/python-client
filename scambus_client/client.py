"""
Main Scambus API client.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import get_api_url, get_api_token, get_api_key_id, get_api_key_secret

from .exceptions import (
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusNotFoundError,
    ScambusServerError,
    ScambusValidationError,
)
from .models import (
    ActionDetails,
    ActivityCompleteDetails,
    AnalysisDetails,
    Case,
    CaseComment,
    ConfidenceOperationDetails,
    ContactDetails,
    DetectionDetails,
    EmailDetails,
    Evidence,
    ExportDetails,
    ExportStream,
    FailedIdentifier,
    Identifier,
    IdentifierLookup,
    ImportDetails,
    JournalEntry,
    Media,
    NoteDetails,
    Notification,
    ObservationDetails,
    Passkey,
    PhoneCallDetails,
    Report,
    ResearchDetails,
    Session,
    Tag,
    TagOperationDetails,
    TagValue,
    TextConversationDetails,
    UpdateDetails,
    ValidationDetails,
    View,
)
from .types import (
    TagLookupInput,
    StreamFilterInput,
    ViewFilterInput,
    ViewSortOrderInput,
    to_dict,
    to_dict_list,
)


def build_identifier_type_filter(identifier_types: Union[str, List[str]], data_type: str = "identifier") -> str:
    """
    Build a JSONPath filter expression for filtering by identifier type(s).

    This is a helper function that generates the filter_expression parameter
    for create_stream() to filter identifiers by type.

    Args:
        identifier_types: Single identifier type or list of types.
                         Valid types: phone, email, url, bank_account,
                         crypto_wallet, social_media, payment_token
        data_type: Stream data type ("identifier" or "journal_entry").
                  This affects the JSONPath expression structure.

    Returns:
        JSONPath filter expression string

    Examples:
        >>> build_identifier_type_filter("phone", data_type="identifier")
        '$.type == "phone"'

        >>> build_identifier_type_filter(["phone", "email"], data_type="identifier")
        '$.type == "phone" || $.type == "email"'

        >>> build_identifier_type_filter("phone", data_type="journal_entry")
        'exists($.identifiers[*] ? (@.type == "phone"))'

        >>> build_identifier_type_filter(["phone", "email"], data_type="journal_entry")
        'exists($.identifiers[*] ? (@.type == "phone" || @.type == "email"))'
    """
    if isinstance(identifier_types, str):
        identifier_types = [identifier_types]

    if not identifier_types:
        raise ValueError("identifier_types cannot be empty")

    # Validate types
    valid_types = {"phone", "email", "url", "bank_account", "crypto_wallet", "social_media", "payment_token"}
    for itype in identifier_types:
        if itype not in valid_types:
            raise ValueError(
                f"Invalid identifier type: {itype}. "
                f"Valid types are: {', '.join(sorted(valid_types))}"
            )

    # Build filter expression based on data_type
    if data_type == "identifier":
        # For identifier streams: check top-level type field
        if len(identifier_types) == 1:
            return f'$.type == "{identifier_types[0]}"'
        else:
            conditions = [f'$.type == "{itype}"' for itype in identifier_types]
            return " || ".join(conditions)
    elif data_type == "journal_entry":
        # For journal entry streams: check identifiers array
        # Use SQL/JSON Path exists() predicate to check if any identifier matches
        if len(identifier_types) == 1:
            return f'exists($.identifiers[*] ? (@.type == "{identifier_types[0]}"))'
        else:
            conditions = [f'@.type == "{itype}"' for itype in identifier_types]
            inner_condition = " || ".join(conditions)
            return f'exists($.identifiers[*] ? ({inner_condition}))'
    else:
        raise ValueError(f"Invalid data_type: {data_type}. Valid types are: identifier, journal_entry")


def build_combined_filter(
    identifier_types: Optional[Union[str, List[str]]] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    custom_expression: Optional[str] = None,
    data_type: str = "identifier"
) -> Optional[str]:
    """
    Build a complex JSONPath filter expression combining multiple conditions.

    This helper function makes it easy to create filter expressions that combine
    identifier type filtering with confidence ranges and custom conditions.

    Args:
        identifier_types: Single type or list of types to filter by
        min_confidence: Minimum confidence score (0.0 to 1.0)
        max_confidence: Maximum confidence score (0.0 to 1.0)
        custom_expression: Additional custom JSONPath expression to AND with other conditions
        data_type: Stream data type ("identifier" or "journal_entry")

    Returns:
        Combined JSONPath filter expression, or None if no conditions specified

    Examples:
        >>> build_combined_filter(identifier_types="phone", min_confidence=0.8, data_type="identifier")
        '$.type == "phone" && $.confidence >= 0.8'

        >>> build_combined_filter(identifier_types=["phone", "email"], min_confidence=0.9, data_type="identifier")
        '($.type == "phone" || $.type == "email") && $.confidence >= 0.9'

        >>> build_combined_filter(identifier_types="phone", data_type="journal_entry")
        'exists($.identifiers[*] ? (@.type == "phone"))'

        >>> build_combined_filter(custom_expression='$.details.platform == "whatsapp"')
        '$.details.platform == "whatsapp"'
    """
    conditions = []

    # Add identifier type filter
    if identifier_types:
        type_filter = build_identifier_type_filter(identifier_types, data_type=data_type)
        # Wrap in parentheses if multiple types (for proper AND precedence)
        if isinstance(identifier_types, list) and len(identifier_types) > 1:
            type_filter = f"({type_filter})"
        conditions.append(type_filter)

    # Add confidence filters
    if min_confidence is not None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        # For journal entry streams, confidence is stored in min_confidence field
        if data_type == "journal_entry":
            conditions.append(f"$.min_confidence >= {min_confidence}")
        else:
            conditions.append(f"$.confidence >= {min_confidence}")

    if max_confidence is not None:
        if not 0 <= max_confidence <= 1:
            raise ValueError("max_confidence must be between 0 and 1")
        # For journal entry streams, confidence is stored in min_confidence field
        if data_type == "journal_entry":
            conditions.append(f"$.min_confidence <= {max_confidence}")
        else:
            conditions.append(f"$.confidence <= {max_confidence}")

    # Add custom expression
    if custom_expression:
        conditions.append(custom_expression)

    if not conditions:
        return None

    # Combine all conditions with AND
    return " && ".join(conditions)


class ScambusClient:
    """
    Client for the Scambus API.

    The client automatically uses authentication from the CLI if you've run `scambus auth login`.
    No configuration needed in most cases!

    Example:
        ```python
        from scambus_client import ScambusClient

        # Initialize client (uses CLI auth automatically)
        client = ScambusClient()

        # Or explicitly provide credentials
        client = ScambusClient(
            api_url="https://scambus.net/api",
            api_token="your-api-token"
        )

        # Upload media
        media = client.upload_media("screenshot.png", notes="Phishing site")

        # Create detection with identifiers
        entry = client.create_detection(
            description="Automated phishing detection",
            identifiers=[
                {"type": "phone", "value": "+12125551234", "confidence": 0.9},
                {"type": "email", "value": "scammer@example.com", "confidence": 0.95}
            ],
            evidence={
                "type": "screenshot",
                "title": "Phishing Website",
                "description": "Screenshot of fraudulent site",
                "source": "Automated Scanner",
                "mediaIds": [media.id]
            }
        )
        ```
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the Scambus client.

        Parameters are loaded with the following priority:
        1. Explicit parameter values passed to __init__
        2. Environment variables
        3. CLI config file (~/.scambus/config.json)
        4. Defaults (api_url: https://scambus.net/api)

        Environment variables:
            SCAMBUS_API_URL (or SCAMBUS_URL): API base URL
            SCAMBUS_API_KEY_ID: API key ID (UUID)
            SCAMBUS_API_KEY_SECRET: API key secret
            SCAMBUS_API_TOKEN: JWT token (legacy)

        Args:
            api_url: Base URL of the Scambus API (default: https://scambus.net/api)
            api_key_id: API key ID (UUID) for authentication
            api_key_secret: API key secret for authentication
            api_token: API JWT token (legacy, prefer api_key_id/api_key_secret)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for failed requests (default: 3)
        """
        # Load configuration with priority: explicit param > env var > config file > default
        api_url = get_api_url(api_url)
        api_key_id = get_api_key_id(api_key_id)
        api_key_secret = get_api_key_secret(api_key_secret)

        # Ensure /api suffix
        if not api_url.endswith("/api"):
            api_url = f"{api_url}/api"

        # Only try to load api_token if api_key auth not available
        if not (api_key_id and api_key_secret):
            api_token = get_api_token(api_token)

        self.api_url = api_url.rstrip("/") if api_url else "https://scambus.net/api"
        self.timeout = timeout

        # Create session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set authentication headers
        if api_key_id and api_key_secret:
            # New format: API key ID and secret
            self.session.headers.update(
                {
                    "X-API-Key": f"{api_key_id}:{api_key_secret}",
                    "User-Agent": "scambus-python-client/1.0.0",
                }
            )
        elif api_token:
            # Legacy format: JWT token
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {api_token}",
                    "User-Agent": "scambus-python-client/1.0.0",
                }
            )
        else:
            raise ValueError(
                "No authentication provided. Either:\n"
                "1. Set SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET environment variables, or\n"
                "2. Provide api_key_id/api_key_secret parameters, or\n"
                "3. Run 'scambus auth login' to authenticate via CLI, or\n"
                "4. Set SCAMBUS_API_TOKEN environment variable"
            )

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: JSON data to send
            data: Form data to send
            files: Files to upload
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            ScambusAuthenticationError: If authentication fails
            ScambusValidationError: If request validation fails
            ScambusNotFoundError: If resource not found
            ScambusServerError: If server error occurs
            ScambusAPIError: For other API errors
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                data=data,
                files=files,
                params=params,
                timeout=self.timeout,
            )

            # Handle error responses
            if response.status_code >= 400:
                self._handle_error_response(response)

            # Return JSON response
            if response.status_code == 204:  # No content
                return {}

            try:
                return response.json()
            except ValueError as json_err:
                # JSON decode failed - provide diagnostic information
                response_preview = response.text[:200] if response.text else "(empty)"
                raise ScambusAPIError(
                    f"Invalid JSON response from {url} "
                    f"(status {response.status_code}): {json_err}. "
                    f"Response body: {response_preview}"
                )

        except requests.exceptions.Timeout as e:
            raise ScambusAPIError(f"Request timeout: {e}")
        except requests.exceptions.ConnectionError as e:
            raise ScambusAPIError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise ScambusAPIError(f"Request failed: {e}")

    def _handle_error_response(self, response: requests.Response):
        """Handle error responses from the API."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", response.text)
        except ValueError:
            error_message = response.text or f"HTTP {response.status_code}"

        if response.status_code == 401:
            raise ScambusAuthenticationError(
                error_message,
                response.status_code,
                error_data if "error_data" in locals() else None,
            )
        elif response.status_code == 400:
            raise ScambusValidationError(
                error_message,
                response.status_code,
                error_data if "error_data" in locals() else None,
            )
        elif response.status_code == 404:
            raise ScambusNotFoundError(
                error_message,
                response.status_code,
                error_data if "error_data" in locals() else None,
            )
        elif response.status_code >= 500:
            raise ScambusServerError(
                error_message,
                response.status_code,
                error_data if "error_data" in locals() else None,
            )
        else:
            raise ScambusAPIError(
                error_message,
                response.status_code,
                error_data if "error_data" in locals() else None,
            )

    # Media Methods

    def upload_media(
        self,
        file_path: Union[str, Path],
        notes: Optional[str] = None,
        journal_entry_id: Optional[str] = None,
    ) -> Media:
        """
        Upload a media file from a file path.

        Args:
            file_path: Path to the file to upload
            notes: Optional notes about the media
            journal_entry_id: Optional journal entry ID to link immediately

        Returns:
            Media object with the uploaded media details

        Example:
            ```python
            media = client.upload_media(
                "phishing-screenshot.png",
                notes="Screenshot of fraudulent banking website"
            )
            print(f"Uploaded media ID: {media.id}")
            ```
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Prepare multipart data
        data = {}
        if notes:
            data["notes"] = notes
        if journal_entry_id:
            data["journalEntryId"] = journal_entry_id

        # Open and upload file
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            response = self._request("POST", "/media/upload", data=data, files=files)

        return Media.from_dict(response)

    def upload_media_from_buffer(
        self,
        buffer: bytes,
        filename: str,
        notes: Optional[str] = None,
        journal_entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Media:
        """
        Upload media from a byte buffer (in-memory file).

        This is useful when you have file data in memory (e.g., from a download,
        API response, or generated content) and don't want to write to disk first.

        Args:
            buffer: Byte buffer containing the file data
            filename: Filename to use for the upload (e.g., "screenshot.png")
            notes: Optional notes about the media
            journal_entry_id: Optional journal entry ID to link immediately
            metadata: Optional metadata dictionary for additional tracking (e.g., test_batch, environment)

        Returns:
            Media object with the uploaded media details

        Example:
            ```python
            import io
            import requests

            # Download image from URL
            response = requests.get("https://example.com/scam-site.png")
            image_data = response.content

            # Upload directly from buffer
            media = client.upload_media_from_buffer(
                buffer=image_data,
                filename="scam-site-screenshot.png",
                notes="Screenshot downloaded from URL"
            )
            print(f"Uploaded media ID: {media.id}")

            # Or with BytesIO
            buffer = io.BytesIO(image_data)
            media = client.upload_media_from_buffer(
                buffer=buffer.getvalue(),
                filename="screenshot.png"
            )
            ```
        """
        # Prepare multipart data
        data = {}
        if notes:
            data["notes"] = notes
        if journal_entry_id:
            data["journalEntryId"] = journal_entry_id
        if metadata:
            # Metadata needs to be JSON-serialized for multipart form data
            import json
            data["metadata"] = json.dumps(metadata)

        # Upload from buffer
        files = {"file": (filename, buffer)}
        response = self._request("POST", "/media/upload", data=data, files=files)

        return Media.from_dict(response)

    def get_media(self, media_id: str) -> Media:
        """
        Get media by ID.

        Args:
            media_id: Media UUID

        Returns:
            Media object
        """
        response = self._request("GET", f"/media/{media_id}")
        return Media.from_dict(response)

    # Journal Entry Methods

    def create_journal_entry(
        self,
        entry_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        performed_at: Optional[datetime] = None,
        case_id: Optional[str] = None,
        identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        parent_journal_entry_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        in_progress: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> JournalEntry:
        """
        Create a journal entry with automatic identifier resolution.

        Args:
            entry_type: Type of journal entry. Valid types:
                - phone_call: Phone call with a suspect
                - email: Email correspondence
                - text_conversation: SMS/text conversation
                - detection: Automated detection or discovery
                - import: Import of data/identifiers
                - export: Export of data/identifiers
                - validation: Validation of identifier
                - note: General note or observation
                - contact_attempt: Attempted contact
                - contact_success: Successful contact
                - evidence_received: Evidence received
                - research: Research activity
                - analysis: Analysis performed
                - action_taken: Action taken on case
                - observation: Observation made
                - update: General update
                - activity_complete: Completion of an in-progress activity
            description: Brief description
            details: Type-specific details
            performed_at: When the action/event occurred
            case_id: Optional case ID to link to
            identifier_lookups: List of identifiers to lookup/create (for scammer/suspect identifiers)
            our_identifier_lookups: List of "our" identifiers to lookup/create (for honeypot/bot identifiers)
            evidence: Optional evidence with media
            parent_journal_entry_id: Optional parent journal entry ID (for linking related entries)
            tags: Optional list of tags to apply. Can be TagLookup objects or dictionaries.
                TagLookup objects: TagLookup(tag_name="Phishing", tag_value="Email")
                Dictionaries: {"tag_name": "Phishing", "tag_value": "Email"}
                The backend will validate these tags exist and return 400 if not found.
            start_time: When the activity started (optional). If set without end_time and in_progress=False,
                end_time defaults to start_time (instant completion)
            end_time: When the activity ended (optional)
            in_progress: If True, creates an in-progress activity (omits end_time from request).
                Use entry.complete() later to mark as complete.
            metadata: Optional metadata dictionary for additional tracking (e.g., test_batch, environment)

        Returns:
            Created JournalEntry object

        Example:
            ```python
            # Automated detection
            entry = client.create_journal_entry(
                entry_type="detection",
                description="Automated phishing detection",
                details={"category": "phishing", "confidence": 0.95},
                identifier_lookups=[
                    {"type": "phone", "value": "+12125551234", "confidence": 0.9},
                    {"type": "email", "value": "scammer@example.com", "confidence": 0.95}
                ],
                evidence={
                    "type": "screenshot",
                    "title": "Phishing Website",
                    "mediaIds": [media_id]
                }
            )

            # In-progress activity
            entry = client.create_journal_entry(
                entry_type="note",
                description="Reviewing case files",
                start_time=datetime.now(),
                in_progress=True  # Omits end_time
            )
            # Complete later with: entry.complete()

            # Instant completion (end_time defaults to start_time)
            entry = client.create_journal_entry(
                entry_type="note",
                description="Quick observation",
                start_time=datetime.now()
                # end_time defaults to start_time
            )

            # Create entry on behalf of another user
            entry = client.create_journal_entry(
                entry_type="note",
                description="User reported suspicious activity",
                originator_type="user",
                originator_identifier="user@example.com",
                create_originator=True  # Create if doesn't exist
            )
            ```
        """
        data = {
            "type": entry_type,
            "description": description,
        }

        if details:
            data["details"] = details

        if performed_at:
            data["performed_at"] = performed_at.isoformat()

        if case_id:
            data["case_id"] = case_id

        # Convert identifier lookups to dictionaries
        if identifier_lookups:
            data["identifier_lookups"] = [
                lookup.to_dict() if isinstance(lookup, IdentifierLookup) else lookup
                for lookup in identifier_lookups
            ]

        # Convert our identifier lookups to dictionaries (for honeypot/bot identifiers)
        if our_identifier_lookups:
            data["our_identifier_lookups"] = [
                lookup.to_dict() if isinstance(lookup, IdentifierLookup) else lookup
                for lookup in our_identifier_lookups
            ]

        # Convert evidence to dictionary
        if evidence:
            data["evidence"] = evidence.to_dict() if isinstance(evidence, Evidence) else evidence

        # Add originator lookup if provided
        if originator_type and originator_identifier:
            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }

        # Add parent journal entry ID if provided
        if parent_journal_entry_id:
            data["parent_journal_entry_id"] = parent_journal_entry_id

        # Add tags if provided (convert TagLookup objects to dictionaries)
        if tags:
            data["tag_lookups"] = to_dict_list(tags)

        # Add metadata if provided
        if metadata:
            data["metadata"] = metadata

        # Handle start_time and end_time
        if start_time:
            data["start_time"] = start_time.isoformat()

            if in_progress:
                # In-progress: omit end_time
                pass
            elif end_time is None:
                # Default end_time to start_time (instant completion)
                data["end_time"] = start_time.isoformat()
            else:
                # Use provided end_time
                data["end_time"] = end_time.isoformat()
        elif end_time:
            # end_time provided without start_time
            data["end_time"] = end_time.isoformat()

        response = self._request("POST", "/journal-entries", json_data=data)

        # Capture failed_identifiers before fetching full entry
        failed_identifiers = None
        if "failed_identifiers" in response:
            failed_identifiers = [
                FailedIdentifier.from_dict(fi) for fi in response["failed_identifiers"]
            ]

        # Backend only returns {"id": "..."}, so fetch the full entry
        entry_id = response["id"]
        entry = self.get_journal_entry(entry_id)

        # Set client reference so entry.complete() works
        entry._client = self

        # Attach failed identifiers from creation response
        entry.failed_identifiers = failed_identifiers

        return entry

    def create_detection(
        self,
        description: str,
        details: Optional[Union[DetectionDetails, Dict[str, Any]]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_journal_entry_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        in_progress: bool = False,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create a 'detection' type journal entry.

        This is a helper that calls create_journal_entry() with type="detection".
        Use this for automated detections, scam discoveries, or security findings.

        Args:
            description: Detection description
            details: Detection details - use DetectionDetails or dict with category, confidence, etc.
            identifiers: List of suspect/scammer identifiers found
            our_identifier_lookups: List of honeypot/bot identifiers (our side)
            evidence: Evidence (screenshots, etc.)
            media: Single Media object or list of Media objects from upload_media()
            case_id: Optional case ID to link this detection to
            tags: Tags to apply to this entry (use TagLookup objects or dicts)
            metadata: Additional metadata for tracking (e.g., test_batch, environment)
            parent_journal_entry_id: Parent entry ID for causal linking
            start_time: When detection started (optional)
            end_time: When detection ended (optional)
            in_progress: If True, creates an in-progress entry (omits end_time)
            originator_type: Optional originator type (user, automation)
            originator_identifier: Identifier for the originator (email, discord username, etc.)
            create_originator: Create originator record if it doesn't exist

        Returns:
            Created JournalEntry object

        Example:
            ```python
            from datetime import datetime, timezone
            from scambus_client import (
                DetectionDetails, IdentifierLookup, TagLookup
            )

            # Using typed classes (recommended)
            entry = client.create_detection(
                description="Phishing website detected",
                details=DetectionDetails(
                    category="phishing",
                    detected_at=datetime.now(timezone.utc),
                    confidence=0.95,
                ),
                identifiers=[
                    IdentifierLookup(
                        type="email",
                        value="scammer@example.com",
                        confidence=0.95,
                    )
                ],
                tags=[
                    TagLookup(tag_name="HighPriority"),
                    TagLookup(tag_name="ScamType", tag_value="Phishing"),
                ],
            )

            # With media files
            media = client.upload_media("screenshot.png")
            entry = client.create_detection(
                description="Phishing site screenshot",
                identifiers=[
                    IdentifierLookup(type="url", value="https://fake-bank.com")
                ],
                media=media,
                tags=[TagLookup(tag_name="EvidenceCollected")],
            )
            ```
        """
        # Handle media parameter
        if media is not None:
            # Convert single media to list
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            # Create or update evidence with media IDs
            if evidence is None:
                # Auto-create evidence from media
                evidence = {
                    "type": (
                        "screenshot" if media_list[0].mime_type.startswith("image/") else "file"
                    ),
                    "title": "Detection Evidence",
                    "description": f"Evidence for detection: {description}",
                    "source": "Automated Detection",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "media_ids": media_ids,
                }
            else:
                # Add media IDs to existing evidence
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        # Handle details - convert DetectionDetails to dict if needed
        details_dict = details
        if isinstance(details, DetectionDetails):
            details_dict = details.to_dict()

        return self.create_journal_entry(
            entry_type="detection",
            description=description,
            details=details_dict,
            performed_at=datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            parent_journal_entry_id=parent_journal_entry_id,
            start_time=start_time,
            end_time=end_time,
            in_progress=in_progress,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
        )

    def create_phone_call(
        self,
        description: str,
        direction: str,
        start_time: datetime,
        end_time: datetime,
        recording_url: Optional[str] = None,
        transcript_url: Optional[str] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_journal_entry_id: Optional[str] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        in_progress: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create a 'phone_call' type journal entry.

        Args:
            description: Description of the phone call
            direction: Call direction ("inbound" or "outbound")
            start_time: When the call started
            end_time: When the call ended
            recording_url: Optional URL to call recording
            transcript_url: Optional URL to call transcript
            identifiers: List of suspect/scammer identifiers (e.g., phone numbers)
            our_identifier_lookups: List of honeypot/bot identifiers (our side)
            evidence: Evidence (recordings, screenshots, etc.)
            media: Single Media object or list of Media objects from upload_media()
            case_id: Optional case ID to link this call to
            tags: Tags to apply to this entry (use TagLookup objects or dicts)
            metadata: Additional metadata for tracking
            parent_journal_entry_id: Parent entry ID for causal linking
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist
            in_progress: If True, creates an in-progress call (omits end_time)

        Returns:
            Created JournalEntry object

        Example:
            ```python
            from datetime import datetime, timedelta, timezone
            from scambus_client import IdentifierLookup, TagLookup

            # Outbound call with typed classes
            now = datetime.now(timezone.utc)
            entry = client.create_phone_call(
                description="Called suspect regarding fraudulent transaction",
                direction="outbound",
                start_time=now,
                end_time=now + timedelta(minutes=5),
                identifiers=[
                    IdentifierLookup(type="phone", value="+12125551234", confidence=1.0)
                ],
                tags=[
                    TagLookup(tag_name="ScamType", tag_value="TechSupport"),
                ],
            )

            # Inbound call with recording and tags
            entry = client.create_phone_call(
                description="Received suspicious call claiming to be IRS",
                direction="inbound",
                start_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 10, 35, tzinfo=timezone.utc),
                recording_url="https://storage.example.com/call-recording.mp3",
                identifiers=[
                    IdentifierLookup(type="phone", value="+18005551234", confidence=0.9)
                ],
                tags=[TagLookup(tag_name="HighPriority")],
            )

            # In-progress call
            entry = client.create_phone_call(
                description="Currently on call",
                direction="outbound",
                start_time=now,
                end_time=now,  # Required but will be ignored when in_progress=True
                in_progress=True,
                identifiers=[
                    IdentifierLookup(type="phone", value="+12125551234", confidence=1.0)
                ],
            )
            # Complete later with: entry.complete()
            ```
        """
        details = PhoneCallDetails(
            direction=direction,
            recording_url=recording_url,
            transcript_url=transcript_url,
        )

        # Handle media parameter
        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "recording" if any(m.mime_type.startswith("audio/") for m in media_list) else "file",
                    "title": "Phone Call Evidence",
                    "description": f"Evidence for phone call: {description}",
                    "source": "Phone Call Recording",
                    "collected_at": start_time.isoformat(),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return self.create_journal_entry(
            entry_type="phone_call",
            description=description,
            details=details.to_dict(),
            performed_at=start_time,
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            parent_journal_entry_id=parent_journal_entry_id,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
            start_time=start_time,
            end_time=end_time,
            in_progress=in_progress,
        )

    def create_email(
        self,
        description: str,
        direction: str,
        subject: str,
        sent_at: datetime,
        body: Optional[str] = None,
        html_body: Optional[str] = None,
        message_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        attachments: Optional[List[str]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_journal_entry_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        in_progress: bool = False,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create an 'email' type journal entry.

        Args:
            description: Description of the email
            direction: Email direction ("inbound" or "outbound")
            subject: Email subject line
            sent_at: When the email was sent
            body: Plain text body (optional)
            html_body: HTML body (optional)
            message_id: Email message ID (optional)
            headers: Email headers as key-value pairs (optional)
            attachments: List of attachment filenames (optional)
            identifiers: List of suspect/scammer identifiers (e.g., email addresses)
            our_identifier_lookups: List of honeypot/bot identifiers (our side)
            media: Single Media object or list of Media objects (e.g., email screenshots)
            evidence: Optional evidence structure
            case_id: Optional case ID to link this email to
            tags: Tags to apply to this entry (use TagLookup objects or dicts)
            metadata: Additional metadata for tracking
            parent_journal_entry_id: Parent entry ID for causal linking
            start_time: When email interaction started (optional)
            end_time: When email interaction ended (optional)
            in_progress: If True, creates an in-progress entry (omits end_time)
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist

        Returns:
            Created JournalEntry object

        Example:
            ```python
            from datetime import datetime, timezone
            from scambus_client import IdentifierLookup, TagLookup

            # Inbound phishing email with typed classes
            entry = client.create_email(
                description="Phishing email impersonating PayPal",
                direction="inbound",
                subject="Urgent: Verify your PayPal account",
                sent_at=datetime(2024, 1, 15, 9, 15, tzinfo=timezone.utc),
                body="Click here to verify your account...",
                message_id="<12345@suspicious-domain.com>",
                headers={
                    "from": "security@paypa1.com",
                    "dkim": "fail"
                },
                identifiers=[
                    IdentifierLookup(type="email", value="security@paypa1.com", confidence=1.0)
                ],
                tags=[
                    TagLookup(tag_name="ScamType", tag_value="Phishing"),
                    TagLookup(tag_name="HighPriority"),
                ],
            )

            # Outbound reply with screenshot
            screenshot = client.upload_media("email-screenshot.png")
            entry = client.create_email(
                description="Reply to phishing email for investigation",
                direction="outbound",
                subject="Re: Verify your PayPal account",
                sent_at=datetime.now(timezone.utc),
                body="I received your email...",
                media=screenshot,
                tags=[TagLookup(tag_name="EvidenceCollected")],
            )
            ```
        """
        details_obj = EmailDetails(
            direction=direction,
            subject=subject,
            sent_at=sent_at,
            body=body,
            html_body=html_body,
            message_id=message_id,
            headers=headers,
            attachments=attachments,
        )

        # Handle media parameter similar to create_detection
        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "screenshot",
                    "title": "Email Evidence",
                    "description": f"Evidence for email: {subject}",
                    "source": "Email Communication",
                    "collectedAt": sent_at.isoformat(),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return self.create_journal_entry(
            entry_type="email",
            description=description,
            details=details_obj.to_dict(),
            performed_at=sent_at,
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            parent_journal_entry_id=parent_journal_entry_id,
            start_time=start_time,
            end_time=end_time,
            in_progress=in_progress,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
        )

    def create_text_conversation(
        self,
        description: str,
        platform: str,
        start_time: datetime,
        end_time: datetime,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_journal_entry_id: Optional[str] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        in_progress: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create a 'text_conversation' type journal entry.

        Args:
            description: Description of the conversation
            platform: Messaging platform (e.g., "SMS", "WhatsApp", "Telegram", "Signal")
            start_time: When the conversation began
            end_time: When the conversation ended
            identifiers: List of suspect/scammer identifiers (e.g., phone numbers, social media handles)
            our_identifier_lookups: List of honeypot/bot identifiers (our side)
            media: Single Media object or list of Media objects (e.g., screenshots)
            evidence: Optional evidence structure
            case_id: Optional case ID to link this conversation to
            tags: Tags to apply to this entry (use TagLookup objects or dicts)
            metadata: Additional metadata for tracking
            parent_journal_entry_id: Parent entry ID for causal linking
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist
            in_progress: If True, creates an in-progress conversation (omits end_time)

        Returns:
            Created JournalEntry object

        Example:
            ```python
            from datetime import datetime, timedelta, timezone
            from scambus_client import IdentifierLookup, TagLookup

            # WhatsApp conversation with typed classes
            start = datetime.now(timezone.utc)
            entry = client.create_text_conversation(
                description="WhatsApp conversation with suspected scammer",
                platform="WhatsApp",
                start_time=start,
                end_time=start + timedelta(hours=1),
                identifiers=[
                    IdentifierLookup(type="phone", value="+12125551234", confidence=0.95)
                ],
                tags=[
                    TagLookup(tag_name="ScamType", tag_value="Romance"),
                ],
            )

            # SMS with screenshots and tags
            screenshot1 = client.upload_media("sms-screenshot-1.png")
            screenshot2 = client.upload_media("sms-screenshot-2.png")
            entry = client.create_text_conversation(
                description="Suspicious SMS messages requesting payment",
                platform="SMS",
                start_time=datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
                media=[screenshot1, screenshot2],
                identifiers=[
                    IdentifierLookup(type="phone", value="+18005551234", confidence=0.9)
                ],
                tags=[TagLookup(tag_name="EvidenceCollected")],
            )

            # In-progress conversation
            entry = client.create_text_conversation(
                description="Ongoing conversation",
                platform="WhatsApp",
                start_time=start,
                end_time=start,  # Required but ignored when in_progress=True
                in_progress=True,
                identifiers=[
                    IdentifierLookup(type="phone", value="+12125551234", confidence=0.95)
                ],
            )
            # Complete later with: entry.complete()
            ```
        """
        details_obj = TextConversationDetails(
            platform=platform,
        )

        # Handle media parameter
        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "screenshot",
                    "title": f"{platform} Conversation Evidence",
                    "description": f"Evidence for {platform} conversation: {description}",
                    "source": f"{platform} Communication",
                    "collectedAt": start_time.isoformat(),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return self.create_journal_entry(
            entry_type="text_conversation",
            description=description,
            details=details_obj.to_dict(),
            performed_at=start_time,
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            parent_journal_entry_id=parent_journal_entry_id,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
            start_time=start_time,
            end_time=end_time,
            in_progress=in_progress,
        )

    def create_note(
        self,
        description: str,
        details: Optional[Union[NoteDetails, Dict[str, Any]]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_journal_entry_id: Optional[str] = None,
        performed_at: Optional[datetime] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        in_progress: bool = False,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create a 'note' type journal entry.

        Args:
            description: Note content/description
            details: Optional additional details - use NoteDetails or dict
            identifiers: List of suspect/scammer identifiers to link
            our_identifier_lookups: List of honeypot/bot identifiers (our side)
            evidence: Evidence to attach (e.g., screenshots, documents)
            media: Single Media object or list of Media objects from upload_media()
            case_id: Optional case ID to link this note to
            tags: Tags to apply to this entry (use TagLookup objects or dicts)
            metadata: Additional metadata for tracking
            parent_journal_entry_id: Parent entry ID for causal linking
            performed_at: When the note was made (defaults to now)
            start_time: When activity started (optional)
            end_time: When activity ended (optional)
            in_progress: If True, creates an in-progress entry (omits end_time)
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist

        Returns:
            Created JournalEntry object

        Example:
            ```python
            from scambus_client import IdentifierLookup, TagLookup, NoteDetails

            # Simple note with typed classes
            entry = client.create_note(
                description="Suspect uses multiple aliases",
                details=NoteDetails(
                    content="Detailed observation about aliases",
                    category="observation",
                ),
                tags=[TagLookup(tag_name="NeedsReview")],
            )

            # Note with identifiers and tags
            entry = client.create_note(
                description="Community member reported suspicious activity",
                identifiers=[
                    IdentifierLookup(type="phone", value="+12125551234", confidence=0.8)
                ],
                tags=[
                    TagLookup(tag_name="CommunityReport"),
                    TagLookup(tag_name="HighPriority"),
                ],
            )

            # Note on behalf of community member
            entry = client.create_note(
                description="Community member flagged this identifier",
                originator_type="community_member",
                originator_identifier="discord_user#1234",
                create_originator=True,
                tags=[TagLookup(tag_name="CommunityReport")],
            )
            ```
        """
        # Handle details - convert NoteDetails to dict if needed
        details_dict = details
        if isinstance(details, NoteDetails):
            details_dict = details.to_dict()

        # Handle media parameter
        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "document",
                    "title": "Note Evidence",
                    "description": f"Evidence for note: {description}",
                    "source": "Note Attachment",
                    "collected_at": (performed_at or datetime.now(timezone.utc)).isoformat(),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return self.create_journal_entry(
            entry_type="note",
            description=description,
            details=details_dict,
            performed_at=performed_at or datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            parent_journal_entry_id=parent_journal_entry_id,
            start_time=start_time,
            end_time=end_time,
            in_progress=in_progress,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
        )

    def create_import(
        self,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        case_id: Optional[str] = None,
        performed_at: Optional[datetime] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create an 'import' type journal entry.

        Use this for tracking data imports and identifier batch uploads.

        Args:
            description: Description of the import
            details: Optional details about the import (source, count, etc.)
            identifiers: List of identifiers being imported
            case_id: Optional case ID
            performed_at: When the import occurred (defaults to now)
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist

        Returns:
            Created JournalEntry object

        Example:
            ```python
            # Import from external source
            entry = client.create_import(
                description="Imported scam database from external feed",
                details={
                    "source": "ScamAlert Database",
                    "count": 150,
                    "format": "CSV"
                },
                identifiers=[
                    {"type": "email", "value": "scam1@example.com", "confidence": 0.85},
                    {"type": "email", "value": "scam2@example.com", "confidence": 0.90},
                ]
            )
            ```
        """
        return self.create_journal_entry(
            entry_type="import",
            description=description,
            details=details,
            performed_at=performed_at or datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
        )

    def create_export(
        self,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        case_id: Optional[str] = None,
        performed_at: Optional[datetime] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
    ) -> JournalEntry:
        """
        Convenience method to create an 'export' type journal entry.

        Use this for tracking data exports and identifier sharing.

        Args:
            description: Description of the export
            details: Optional details about the export (destination, count, etc.)
            identifiers: List of identifiers being exported
            case_id: Optional case ID
            performed_at: When the export occurred (defaults to now)
            originator_type: Optional originator type
            originator_identifier: Identifier for the originator
            create_originator: Create originator record if it doesn't exist

        Returns:
            Created JournalEntry object

        Example:
            ```python
            # Export to law enforcement
            entry = client.create_export(
                description="Exported high-confidence identifiers to law enforcement",
                details={
                    "destination": "FBI Cyber Division",
                    "count": 50,
                    "format": "JSON",
                    "ticket": "FBI-2024-001234"
                },
                identifiers=[
                    {"type": "email", "value": "scammer@example.com", "confidence": 0.95}
                ]
            )
            ```
        """
        return self.create_journal_entry(
            entry_type="export",
            description=description,
            details=details,
            performed_at=performed_at or datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
        )

    def get_journal_entry(self, entry_id: str) -> JournalEntry:
        """
        Get journal entry by ID.

        Args:
            entry_id: Journal entry UUID

        Returns:
            JournalEntry object
        """
        response = self._request("GET", f"/journal-entries/{entry_id}")

        # Backend returns: {"journal_entry": {"journal_entry": {...}, "can_edit": bool}, "cases": [...]}
        # Extract the nested journal_entry object
        journal_entry_data = response["journal_entry"]["journal_entry"]
        entry = JournalEntry.from_dict(journal_entry_data)

        # Set client reference so entry.complete() works
        entry._client = self

        return entry

    def delete_journal_entry(self, entry_id: str) -> bool:
        """
        Delete a journal entry by ID.

        Args:
            entry_id: Journal entry UUID to delete

        Returns:
            True if successfully deleted

        Raises:
            Exception: If deletion fails (permission denied, not found, etc.)
        """
        self._request("DELETE", f"/journal-entries/{entry_id}")
        return True

    def complete_activity(
        self,
        parent_entry: Union[str, JournalEntry],
        end_time: Optional[datetime] = None,
        completion_reason: str = "manual",
        description: Optional[str] = None,
    ) -> JournalEntry:
        """
        Complete an in-progress activity by creating an activity_complete journal entry.

        Args:
            parent_entry: Parent journal entry (JournalEntry object or entry ID string)
            end_time: When the activity was completed (defaults to now)
            completion_reason: Reason for completion (default: "manual")
            description: Optional description (defaults to auto-generated)

        Returns:
            The created activity_complete journal entry

        Example:
            # Complete using entry object
            entry = client.create_journal_entry(
                entry_type="phone_call",
                description="Customer support call",
                start_time=datetime.now(),
                in_progress=True
            )
            completion = entry.complete()

            # Complete using entry ID
            completion = client.complete_activity("entry-id-123")
        """
        # Extract parent ID and start time
        if isinstance(parent_entry, str):
            parent_id = parent_entry
            # Fetch the parent entry to get start_time
            parent = self.get_journal_entry(parent_id)
            start_time = parent.start_time
            if not start_time:
                raise ValueError(
                    f"Parent entry {parent_id} does not have a start_time. "
                    "Cannot complete an activity without a start time."
                )
        elif isinstance(parent_entry, JournalEntry):
            parent_id = parent_entry.id
            start_time = parent_entry.start_time
            if not start_time:
                raise ValueError(
                    "Parent entry does not have a start_time. "
                    "Cannot complete an activity without a start time."
                )
        else:
            raise TypeError(f"parent_entry must be str or JournalEntry, got {type(parent_entry)}")

        # Default end_time to now (timezone-aware)
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Calculate duration in seconds
        duration_seconds = int((end_time - start_time).total_seconds())

        # Create ActivityCompleteDetails
        details = ActivityCompleteDetails(
            completion_reason=completion_reason,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
        )

        # Auto-generate description if not provided
        if description is None:
            description = f"Activity completed ({completion_reason})"

        # Create activity_complete journal entry
        return self.create_journal_entry(
            entry_type="activity_complete",
            description=description,
            details=details.to_dict(),
            parent_journal_entry_id=parent_id,
        )

    def list_journal_entries(
        self,
        entry_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[JournalEntry]:
        """
        List journal entries.

        Args:
            entry_type: Filter by entry type
            page: Page number (default: 1)
            limit: Items per page (default: 20)

        Returns:
            List of JournalEntry objects
        """
        params = {"page": page, "limit": limit}
        if entry_type:
            params["type"] = entry_type

        response = self._request("GET", "/journal-entries", params=params)

        # Handle paginated response
        # Backend returns: {"data": [{"journal_entry": {...}, "can_edit": bool}, ...]}
        if isinstance(response, dict) and "data" in response:
            return [JournalEntry.from_dict(item["journal_entry"]) for item in response["data"]]
        else:
            return []

    def query_journal_entries(
        self,
        search_query: Optional[str] = None,
        entry_type: Optional[str] = None,
        originator_type: Optional[str] = None,
        originator_id: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        performed_after: Optional[Union[str, datetime]] = None,
        performed_before: Optional[Union[str, datetime]] = None,
        details: Optional[Dict[str, Any]] = None,
        order_by: str = "performed_at",
        order_desc: bool = True,
        cursor: Optional[str] = None,
        include_identifiers: bool = False,
        include_evidence: bool = False,
        parent_journal_entry_id: Optional[str] = None,
        include_children: bool = False,
    ) -> Dict[str, Any]:
        """
        Query journal entries with advanced filtering (page size fixed at 100).

        Args:
            search_query: Full-text search in description
            entry_type: Filter by entry type (phone_call, email, etc.)
            originator_type: Filter by originator type
            originator_id: Filter by specific originator ID
            min_confidence: Minimum confidence score (0.0-1.0)
            max_confidence: Maximum confidence score (0.0-1.0)
            performed_after: Filter entries performed after this time (ISO string or datetime)
            performed_before: Filter entries performed before this time (ISO string or datetime)
            details: JSONB details filters (e.g., {"direction": "inbound", "platform": "pstn"})
            order_by: Column to sort by (default: "performed_at")
            order_desc: Sort descending (default: True)
            cursor: Cursor for pagination (UUID from previous response)
            include_identifiers: Include related identifiers in response
            include_evidence: Include related evidence in response
            parent_journal_entry_id: Query children of a specific parent entry
            include_children: Include child entries in results (default: only shows top-level entries)

        Returns:
            Dict with keys:
                - data: List of JournalEntry objects
                - nextCursor: Cursor for next page (str or None)
                - hasMore: Whether more results exist (bool)
                - count: Number of results in this page (int)

        Example:
            ```python
            # Search for inbound phone calls
            result = client.query_journal_entries(
                entry_type="phone_call",
                details={"direction": "inbound"},
                min_confidence=0.5,
                performed_after="2025-01-01T00:00:00Z"
            )

            for entry in result['data']:
                print(f"{entry.description} - {entry.performed_at}")

            # Fetch next page
            if result['hasMore']:
                next_result = client.query_journal_entries(
                    entry_type="phone_call",
                    details={"direction": "inbound"},
                    cursor=result['nextCursor']
                )
            ```
        """
        # Build request body
        body: Dict[str, Any] = {
            "orderBy": order_by,
            "orderDesc": order_desc,
            "includeIdentifiers": include_identifiers,
            "includeEvidence": include_evidence,
        }

        if search_query:
            body["searchQuery"] = search_query
        if entry_type:
            body["type"] = entry_type
        if originator_type:
            body["originatorType"] = originator_type
        if originator_id:
            body["originatorId"] = originator_id
        if min_confidence is not None:
            body["minConfidence"] = min_confidence
        if max_confidence is not None:
            body["maxConfidence"] = max_confidence
        if cursor:
            body["cursor"] = cursor

        # Handle datetime objects
        if performed_after:
            if isinstance(performed_after, datetime):
                body["performedAfter"] = performed_after.isoformat()
            else:
                body["performedAfter"] = performed_after

        if performed_before:
            if isinstance(performed_before, datetime):
                body["performedBefore"] = performed_before.isoformat()
            else:
                body["performedBefore"] = performed_before

        if details:
            body["details"] = details

        if parent_journal_entry_id:
            body["parentJournalEntryId"] = parent_journal_entry_id
        if include_children:
            body["includeChildren"] = include_children

        # Make request
        response = self._request("POST", "/journal/query", json_data=body)

        # Parse response
        return {
            "data": [JournalEntry.from_dict(entry) for entry in (response.get("data") or [])],
            "nextCursor": response.get("nextCursor"),
            "hasMore": response.get("hasMore", False),
            "count": response.get("count", 0),
        }

    def create_stream_from_query(
        self,
        name: str,
        entry_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        performed_after: Optional[Union[str, datetime]] = None,
        performed_before: Optional[Union[str, datetime]] = None,
        search_query: Optional[str] = None,
    ) -> ExportStream:
        """
        Create a temporary export stream from query parameters.

        This creates a temporary stream that is automatically cleaned up after
        1 hour of inactivity. Useful for following query results in real-time via WebSocket.

        Args:
            name: Stream name
            entry_type: Filter by entry type
            min_confidence: Minimum confidence score
            max_confidence: Maximum confidence score
            performed_after: Start date filter
            performed_before: End date filter
            search_query: Full-text search query

        Returns:
            ExportStream object with the new temporary stream details
        """
        from .types import ViewFilter
        import json

        # Build filter from query parameters
        filter_params = ViewFilter(
            entry_types=[entry_type] if entry_type else None,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            performed_after=performed_after.isoformat() if isinstance(performed_after, datetime) else performed_after,
            performed_before=performed_before.isoformat() if isinstance(performed_before, datetime) else performed_before,
            search_query=search_query,
        )

        # Create temporary stream via dedicated endpoint
        data = {
            "name": name,
            "data_type": "journal_entry",
            "filter_expression": json.dumps(filter_params.to_dict()),
        }

        response = self._request("POST", "/export-streams/temporary", json_data=data)
        return ExportStream.from_dict(response)

    def get_in_progress_activities(self) -> List[JournalEntry]:
        """
        Get journal entries that are currently in progress.

        These are entries with a start_time but no end_time, representing
        ongoing activities like phone calls or conversations.

        Returns:
            List of JournalEntry objects representing in-progress activities
        """
        response = self._request("GET", "/journal-entries/in-progress")

        # Handle response
        if isinstance(response, list):
            return [JournalEntry.from_dict(entry) for entry in response]
        return []

    # View Methods

    def list_views(self) -> List[View]:
        """
        List all available views (saved queries).

        Returns:
            List of View objects
        """
        response = self._request("GET", "/views")

        if isinstance(response, list):
            return [View.from_dict(view) for view in response]
        return []

    def get_view(self, view_id: str) -> View:
        """
        Get a specific view by ID.

        Args:
            view_id: View UUID or alias (e.g., "my-journal-entries")

        Returns:
            View object
        """
        response = self._request("GET", f"/views/{view_id}")
        return View.from_dict(response)

    def execute_view(
        self,
        view_id: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a saved view query.

        Args:
            view_id: View UUID or alias
            cursor: Pagination cursor (optional)
            limit: Results limit (optional)

        Returns:
            Dict with 'data', 'nextCursor', 'hasMore', 'count' keys
            The 'data' field contains the appropriate model objects based on the view's entity_type
        """
        body = {}
        if cursor:
            body["cursor"] = cursor
        if limit:
            body["limit"] = limit

        response = self._request("POST", f"/views/{view_id}/execute", json_data=body)

        # Parse response based on entity type
        # Note: The caller needs to know the entity_type to properly parse the data
        return {
            "data": response.get("data") or [],
            "nextCursor": response.get("nextCursor"),
            "hasMore": response.get("hasMore", False),
            "count": response.get("count", 0),
            "entity_type": response.get("entity_type", "journal"),
        }

    def create_view(
        self,
        name: str,
        entity_type: str,
        filter_criteria: Optional[ViewFilterInput] = None,
        sort_order: Optional[ViewSortOrderInput] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        visibility: str = "organization",
        view_type: str = "standard",
    ) -> View:
        """
        Create a new view (saved query).

        Args:
            name: View name
            entity_type: Type of entities ("cases", "identifiers", "evidence", "journal")
            filter_criteria: Filter criteria (ViewFilter object or dict)
            sort_order: Sort configuration (ViewSortOrder object or dict)
            description: View description (optional)
            alias: Short alias for the view (optional)
            visibility: "private", "organization", or "public" (default: "organization")
            view_type: "standard" or "journal_entry" (default: "standard")

        Returns:
            Created View object

        Example:
            view = client.create_view(
                name="High Confidence Detections",
                entity_type="journal",
                filter_criteria=ViewFilter(
                    min_confidence=0.9,
                    entry_types=["detection"]
                ),
                sort_order=ViewSortOrder(field="created_at", direction="desc")
            )
        """
        body = {
            "name": name,
            "entity_type": entity_type,
            "visibility": visibility,
            "view_type": view_type,
        }

        if description:
            body["description"] = description
        if alias:
            body["alias"] = alias
        if filter_criteria:
            body["filter_criteria"] = to_dict(filter_criteria)
        if sort_order:
            body["sort_order"] = to_dict(sort_order)

        response = self._request("POST", "/views", json_data=body)
        return View.from_dict(response)

    def update_view(
        self,
        view_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        filter_criteria: Optional[ViewFilterInput] = None,
        sort_order: Optional[ViewSortOrderInput] = None,
        visibility: Optional[str] = None,
    ) -> View:
        """
        Update an existing view.

        Args:
            view_id: View UUID
            name: New name (optional)
            description: New description (optional)
            filter_criteria: New filter criteria (optional)
            sort_order: New sort order (optional)
            visibility: New visibility (optional)

        Returns:
            Updated View object
        """
        body = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if filter_criteria is not None:
            body["filter_criteria"] = to_dict(filter_criteria)
        if sort_order is not None:
            body["sort_order"] = to_dict(sort_order)
        if visibility is not None:
            body["visibility"] = visibility

        response = self._request("PUT", f"/views/{view_id}", json_data=body)
        return View.from_dict(response)

    def delete_view(self, view_id: str) -> None:
        """
        Delete a view.

        Args:
            view_id: View UUID
        """
        self._request("DELETE", f"/views/{view_id}")

    def get_my_journal_entries_view(self) -> View:
        """
        Get the "My Journal Entries" system view object.

        This is a shortcut for getting the view definition.
        To execute it, use execute_view() with the returned view's ID.

        Returns:
            View object
        """
        response = self._request("GET", "/views/my-journal-entries")
        return View.from_dict(response)

    def get_my_pinboard_view(self) -> View:
        """
        Get the "My Pinboard" system view object.

        This is a shortcut for getting the view definition.
        To execute it, use execute_view() with the returned view's ID.

        Returns:
            View object
        """
        response = self._request("GET", "/views/my-pinboard")
        return View.from_dict(response)

    def execute_my_journal_entries(self, cursor: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute the "My Journal Entries" view and return results.

        This combines getting the view and executing it in one call.

        Args:
            cursor: Pagination cursor (optional)
            limit: Results limit (optional)

        Returns:
            Dict with 'data', 'nextCursor', 'hasMore', 'count' keys
        """
        view = self.get_my_journal_entries_view()
        return self.execute_view(view.id, cursor=cursor, limit=limit)

    def execute_my_pinboard(self, cursor: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute the "My Pinboard" view and return results.

        This combines getting the view and executing it in one call.

        Args:
            cursor: Pagination cursor (optional)
            limit: Results limit (optional)

        Returns:
            Dict with 'data', 'nextCursor', 'hasMore', 'count' keys
        """
        view = self.get_my_pinboard_view()
        return self.execute_view(view.id, cursor=cursor, limit=limit)

    # Identifier Methods

    def list_identifiers(
        self,
        identifier_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[Identifier]:
        """
        List identifiers.

        Args:
            identifier_type: Filter by type (phone, email, etc.)
            page: Page number (default: 1)
            limit: Items per page (default: 20)

        Returns:
            List of Identifier objects
        """
        params = {"page": page, "limit": limit}
        if identifier_type:
            params["type"] = identifier_type

        response = self._request("GET", "/identifiers", params=params)

        # Handle paginated response
        if isinstance(response, dict) and "data" in response:
            return [Identifier.from_dict(identifier) for identifier in response["data"]]
        else:
            return []

    def get_identifier(self, identifier_id: str) -> Identifier:
        """
        Get identifier by ID.

        Args:
            identifier_id: Identifier UUID

        Returns:
            Identifier object
        """
        response = self._request("GET", f"/identifiers/{identifier_id}")
        return Identifier.from_dict(response)

    # Helper Methods

    def create_bank_account_identifier(
        self,
        account: str,
        routing: str,
        institution: str,
        owner: Optional[str] = None,
        owner_address: Optional[str] = None,
        country: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Helper to create a properly formatted bank account identifier lookup.

        Args:
            account: Account number
            routing: Routing number (9-digit US routing number)
            institution: Bank/institution name (used as fallback)
            owner: Optional account owner name
            owner_address: Optional account owner address
            country: Optional country code (e.g., "US")
            confidence: Optional confidence score (0.0-1.0)

        Returns:
            Dictionary ready for use in identifier_lookups

        Note:
            The server will automatically populate a `routingBank` field by looking up
            the bank name from the routing number using the Federal Reserve's FedACH
            directory. The `institution` parameter is still required as a fallback.

        Example:
            ```python
            bank_identifier = client.create_bank_account_identifier(
                account="9876543210",
                routing="021000021",  # JPMorgan Chase routing number
                institution="Chase Bank",
                country="US",
                confidence=0.85
            )

            entry = client.create_detection(
                description="Scam detected",
                identifiers=[bank_identifier]
            )
            # The resulting identifier will have routingBank="JPMorgan Chase Bank"
            # automatically populated from the routing number
            ```
        """
        bank_data = {
            "account": account,
            "routing": routing,
            "institution": institution,
        }

        if owner:
            bank_data["owner"] = owner
        if owner_address:
            bank_data["ownerAddress"] = owner_address
        if country:
            bank_data["country"] = country

        result = {
            "type": "bank_account",
            "value": json.dumps(bank_data),
        }

        if confidence is not None:
            result["confidence"] = confidence

        return result

    # Case Methods

    def list_cases(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Case]:
        """
        List cases with optional filtering.

        Args:
            page: Page number (default: 1)
            limit: Items per page (default: 20)
            status: Filter by status (active, closed, etc.)
            priority: Filter by priority (low, medium, high, critical)
            category: Filter by category

        Returns:
            List of Case objects

        Example:
            ```python
            # List all active cases
            cases = client.list_cases(status="active")
            for case in cases:
                print(f"{case.title}: {case.status}")

            # Paginate through cases
            page1 = client.list_cases(page=1, limit=10)
            page2 = client.list_cases(page=2, limit=10)

            # Filter by priority and status
            high_priority = client.list_cases(status="active", priority="high")
            ```
        """
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if category:
            params["category"] = category

        response = self._request("GET", "/cases", params=params)

        # Handle paginated response
        if isinstance(response, dict) and "data" in response:
            return [Case.from_dict(case) for case in response["data"]]
        else:
            return []

    def get_case(self, case_id: str) -> Case:
        """
        Get case by ID.

        Args:
            case_id: Case UUID

        Returns:
            Case object

        Example:
            ```python
            case = client.get_case("abc-123-def-456")
            print(f"Case: {case.title}")
            print(f"Status: {case.status}")
            print(f"Description: {case.description}")
            ```
        """
        response = self._request("GET", f"/cases/{case_id}")
        return Case.from_dict(response)

    def create_case(
        self,
        title: str,
        notes: Optional[str] = None,
        status: str = "open",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Case:
        """
        Create a new case.

        Args:
            title: Case title
            notes: Case investigation notes (optional, markdown supported)
            status: Case status (default: "open")
            priority: Case priority (default: "medium")
            metadata: Optional metadata dictionary for additional tracking (e.g., test_batch, environment)

        Returns:
            Created Case object

        Example:
            ```python
            case = client.create_case(
                title="Phishing Campaign - January 2025",
                notes="Large-scale phishing operation targeting financial institutions",
                status="open",
                priority="high"
            )
            print(f"Created case: {case.id}")
            ```
        """
        data = {
            "title": title,
            "status": status,
            "priority": priority,
        }
        if notes:
            data["notes"] = notes
        if metadata:
            data["metadata"] = metadata

        response = self._request("POST", "/cases", json_data=data)
        return Case.from_dict(response)

    def update_case(
        self,
        case_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Case:
        """
        Update an existing case.

        Args:
            case_id: Case UUID
            title: New title (optional)
            notes: New investigation notes (optional)
            status: New status (optional)
            priority: New priority (optional)

        Returns:
            Updated Case object

        Example:
            ```python
            # Update case status
            case = client.update_case(
                case_id="abc-123",
                status="closed"
            )

            # Update title and notes
            case = client.update_case(
                case_id="abc-123",
                title="Updated Title",
                notes="Updated investigation notes"
            )
            ```
        """
        data = {}
        if title is not None:
            data["title"] = title
        if notes is not None:
            data["notes"] = notes
        if status is not None:
            data["status"] = status
        if priority is not None:
            data["priority"] = priority

        if not data:
            raise ScambusValidationError("At least one field must be provided for update")

        self._request("PUT", f"/cases/{case_id}", json_data=data)

        # Backend returns 204 No Content, so fetch the updated case
        return self.get_case(case_id)

    def delete_case(self, case_id: str) -> None:
        """
        Delete a case.

        Args:
            case_id: Case UUID

        Example:
            ```python
            client.delete_case("abc-123-def-456")
            ```
        """
        self._request("DELETE", f"/cases/{case_id}")

    # Automation Methods

    def list_streams(
        self,
        active: Optional[bool] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List all export streams.

        Args:
            active: Filter by active status (True for active only, False for inactive only)
            page: Page number for pagination
            limit: Items per page

        Returns:
            Dictionary with 'data' (list of ExportStream objects) and 'pagination' (pagination info)

        Example:
            ```python
            result = client.list_streams()
            streams = result['data']
            pagination = result['pagination']

            for stream in streams:
                print(f"{stream.name}: {stream.data_type} ({'active' if stream.is_active else 'inactive'})")

            print(f"Page {pagination['page']} of {pagination['total_pages']}")

            # Filter for active streams only
            result = client.list_streams(active=True)

            # With pagination
            page1 = client.list_streams(page=1, limit=10)
            ```
        """
        params = {}
        if active is not None:
            params["active"] = "true" if active else "false"
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        response = self._request("GET", "/export-streams", params=params if params else None)

        if isinstance(response, dict) and "data" in response:
            # Return full response with pagination info
            return {
                'data': [ExportStream.from_dict(s) for s in response["data"]],
                'pagination': response.get('pagination', {})
            }
        else:
            return {'data': [], 'pagination': {}}

    @staticmethod
    def build_stream_filter(
        entry_type: Optional[str] = None,
        direction: Optional[str] = None,
        min_confidence: Optional[float] = None,
        identifier_type: Optional[str] = None,
        has_parent: Optional[bool] = None,
        has_batch: Optional[bool] = None,
        details: Optional[
            Union[
                Dict[str, Any],
                PhoneCallDetails,
                EmailDetails,
                TextConversationDetails,
                DetectionDetails,
                ImportDetails,
                ExportDetails,
                ValidationDetails,
                ContactDetails,
                ResearchDetails,
                AnalysisDetails,
                ActionDetails,
                ObservationDetails,
                NoteDetails,
                UpdateDetails,
                TagOperationDetails,
                ConfidenceOperationDetails,
            ]
        ] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Build a JSONPath filter expression for stream filtering.

        Filterable fields:
        - type: Journal entry type (phone_call, email, detection, etc.)
        - description: Entry description text
        - details: JSONB field (access via details.fieldname)
        - metadata: JSONB field (access via metadata.fieldname)
        - performedAt: Timestamp when action occurred
        - createdAt: Entry creation timestamp
        - parentJournalEntryId: Has parent entry (causal relationship)
        - batchId: Batch identifier for grouped entries
        - originatorKarma: Karma score (for karma_adjustment entries)
        - identifiers: Array of linked identifiers (can filter by type/confidence)

        Args:
            entry_type: Journal entry type (e.g., "phone_call", "email", "detection")
            direction: Call/message direction ("inbound" or "outbound") - shortcut for details.direction
            min_confidence: Minimum confidence threshold for identifiers
            identifier_type: Filter by specific identifier type (e.g., "phone", "email")
            has_parent: Filter entries with/without parent entries
            has_batch: Filter entries with/without batch ID
            details: Details field filters - can be a dictionary or typed Details object
                     (e.g., {"platform": "pstn"} or PhoneCallDetails(...))
            metadata: Dictionary of metadata field filters (e.g., {"source": "automated_scan"})
            **kwargs: Additional custom filter criteria (field: value pairs)
                     Use dot notation for nested fields: "performedAt", "createdAt", "originatorKarma"

        Returns:
            JSONPath filter expression string

        Examples:
            ```python
            # Filter for inbound phone calls
            filter_expr = ScambusClient.build_stream_filter(
                entry_type="phone_call",
                direction="inbound"
            )

            # Filter for high-confidence phone identifiers
            filter_expr = ScambusClient.build_stream_filter(
                identifier_type="phone",
                min_confidence=0.8
            )

            # Filter using dictionary
            filter_expr = ScambusClient.build_stream_filter(
                entry_type="phone_call",
                details={"direction": "inbound"},
                metadata={"source": "automated_scan"}
            )

            # Filter using typed Details object (type-safe!)
            from datetime import datetime, timezone
            phone_details = PhoneCallDetails(
                direction="inbound",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc)
            )
            filter_expr = ScambusClient.build_stream_filter(
                entry_type="phone_call",
                details=phone_details
            )

            # Filter for entries with parent (follow-up actions)
            filter_expr = ScambusClient.build_stream_filter(
                entry_type="validation",
                has_parent=True
            )

            # Custom filter with nested details field
            filter_expr = ScambusClient.build_stream_filter(
                entry_type="phone_call",
                **{"details.platform": "pstn", "details.duration": 120}
            )
            ```
        """
        conditions = []

        # Entry type filter
        if entry_type:
            conditions.append(f"@.type == '{entry_type}'")

        # Direction shortcut (common field in phone_call/email details)
        if direction:
            conditions.append(f"@.details.direction == '{direction}'")

        # Identifier confidence filter
        if min_confidence is not None:
            conditions.append(f"@.identifiers[?(@.confidence >= {min_confidence})]")

        # Identifier type filter
        if identifier_type:
            conditions.append(f"@.identifiers[?(@.type == '{identifier_type}')]")

        # Parent relationship filter
        if has_parent is not None:
            if has_parent:
                conditions.append("@.parentJournalEntryId")  # Has parent
            else:
                conditions.append("!@.parentJournalEntryId")  # No parent

        # Batch relationship filter
        if has_batch is not None:
            if has_batch:
                conditions.append("@.batchId")
            else:
                conditions.append("!@.batchId")

        # Details filters (JSONB field)
        if details:
            # Convert typed Details objects to dict
            if hasattr(details, "to_dict"):
                details_dict = details.to_dict()
            else:
                details_dict = details

            for key, value in details_dict.items():
                if isinstance(value, str):
                    conditions.append(f"@.details.{key} == '{value}'")
                elif isinstance(value, (int, float)):
                    conditions.append(f"@.details.{key} == {value}")
                elif isinstance(value, bool):
                    conditions.append(f"@.details.{key} == {str(value).lower()}")

        # Metadata filters (JSONB field)
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, str):
                    conditions.append(f"@.metadata.{key} == '{value}'")
                elif isinstance(value, (int, float)):
                    conditions.append(f"@.metadata.{key} == {value}")
                elif isinstance(value, bool):
                    conditions.append(f"@.metadata.{key} == {str(value).lower()}")

        # Add custom filters (supports dot notation for nested fields)
        for field, value in kwargs.items():
            if isinstance(value, str):
                conditions.append(f"@.{field} == '{value}'")
            elif isinstance(value, (int, float)):
                conditions.append(f"@.{field} == {value}")
            elif isinstance(value, bool):
                conditions.append(f"@.{field} == {str(value).lower()}")

        if not conditions:
            return ""

        # Build JSONPath expression
        return "$[?(" + " && ".join(conditions) + ")]"

    def get_stream(self, stream_id: str) -> ExportStream:
        """
        Get export stream by ID.

        Args:
            stream_id: Stream UUID

        Returns:
            ExportStream object

        Example:
            ```python
            stream = client.get_stream("abc-123")
            print(f"Stream: {stream.name}")
            print(f"Types: {stream.identifier_types}")
            print(f"Confidence range: {stream.min_confidence} - {stream.max_confidence}")
            ```
        """
        response = self._request("GET", f"/export-streams/{stream_id}")
        return ExportStream.from_dict(response)

    def create_stream(
        self,
        name: str,
        data_type: str = "journal_entry",
        identifier_types: Optional[Union[str, List[str]]] = None,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        is_active: bool = True,
        retention_days: Optional[int] = None,
        backfill_historical: bool = False,
        backfill_from_date: Optional[str] = None,
        filter_expression: Optional[str] = None,
    ) -> ExportStream:
        """
        Create a new export stream.

        Args:
            name: Stream name
            data_type: Stream data type ("journal_entry" or "identifier")
            identifier_types: Identifier type(s) to filter. Can be a single string or list.
                            Valid types: phone, email, url, bank_account, crypto_wallet,
                            social_media, payment_token.
                            Automatically converted to filter_expression. (optional)
            min_confidence: Minimum confidence score (0.0-1.0, default: 0.0)
            max_confidence: Maximum confidence score (0.0-1.0, default: 1.0)
            is_active: Whether stream is active (default: True)
            retention_days: Days to retain data (default: 30)
            backfill_historical: Trigger backfill after creating stream (default: False)
            backfill_from_date: Only backfill from this date (RFC3339 format, optional)
            filter_expression: Custom JSONPath filter expression (optional).
                             If identifier_types is also provided, the expressions will be
                             combined with AND logic.

        Returns:
            Created ExportStream object

        Examples:
            ```python
            # Filter by single identifier type
            stream = client.create_stream(
                name="phone-numbers",
                data_type="identifier",
                identifier_types="phone",
                min_confidence=0.8
            )

            # Filter by multiple identifier types
            stream = client.create_stream(
                name="contact-info",
                data_type="identifier",
                identifier_types=["phone", "email"],
                min_confidence=0.9
            )

            # Use custom filter expression
            stream = client.create_stream(
                name="whatsapp-only",
                data_type="identifier",
                identifier_types="social_media",
                filter_expression='$.details.platform == "whatsapp"'
            )

            # For advanced users: Use filter_expression directly
            stream = client.create_stream(
                name="advanced-filter",
                data_type="identifier",
                filter_expression='($.type == "phone" || $.type == "email") && $.confidence >= 0.95'
            )
            ```

        Note:
            The identifier_types parameter is a convenience helper that automatically
            generates the appropriate filter_expression. You can also provide
            filter_expression directly for more complex filtering needs.
        """
        # Build filter expression from identifier_types if provided
        combined_filter = filter_expression
        if identifier_types:
            type_filter = build_identifier_type_filter(identifier_types, data_type=data_type)
            if combined_filter:
                # Combine with existing filter using AND
                combined_filter = f"({type_filter}) && ({combined_filter})"
            else:
                combined_filter = type_filter

        data = {
            "name": name,
            "data_type": data_type,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "is_active": is_active,
            "backfill_historical": backfill_historical,
        }

        if retention_days is not None:
            data["retention_days"] = retention_days
        if backfill_from_date:
            data["backfill_from_date"] = backfill_from_date
        if combined_filter:
            data["filter_expression"] = combined_filter

        response = self._request("POST", "/export-streams", json_data=data)
        return ExportStream.from_dict(response)

    def create_temporary_stream(
        self,
        data_type: str = "identifier",
        identifier_types: Optional[Union[str, List[str]]] = None,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        filter_expression: Optional[str] = None,
        name: Optional[str] = None,
        view_id: Optional[str] = None,
    ) -> ExportStream:
        """
        Create a temporary export stream that is automatically cleaned up after 1 hour of inactivity.

        Args:
            data_type: Stream data type ("journal_entry" or "identifier")
            identifier_types: Identifier type(s) to filter (optional)
            min_confidence: Minimum confidence score (0.0-1.0, default: 0.0)
            max_confidence: Maximum confidence score (0.0-1.0, default: 1.0)
            filter_expression: Custom JSONPath filter expression (optional)
            name: Stream name (auto-generated if not provided)
            view_id: View ID to use for filtering (stream will match view's filter criteria) (optional)

        Returns:
            Created ExportStream object

        Example:
            ```python
            # Create temporary phone stream
            stream = client.create_temporary_stream(
                data_type="identifier",
                identifier_types="phone",
                min_confidence=0.8
            )

            # Create temporary stream for a specific view
            stream = client.create_temporary_stream(
                view_id="my-view-id",
                data_type="journal_entry"
            )
            ```
        """
        # Build filter expression from identifier_types if provided
        combined_filter = filter_expression
        if identifier_types:
            type_filter = build_identifier_type_filter(identifier_types, data_type=data_type)
            if combined_filter:
                combined_filter = f"({type_filter}) && ({combined_filter})"
            else:
                combined_filter = type_filter

        data = {
            "data_type": data_type,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
        }

        if name:
            data["name"] = name
        if combined_filter:
            data["filter_expression"] = combined_filter
        if view_id:
            data["view_id"] = view_id

        response = self._request("POST", "/export-streams/temporary", json_data=data)
        return ExportStream.from_dict(response)

    def delete_stream(self, stream_id: str) -> None:
        """
        Delete an export stream.

        Args:
            stream_id: Stream UUID

        Example:
            ```python
            client.delete_stream("abc-123")
            ```
        """
        self._request("DELETE", f"/export-streams/{stream_id}")

    def consume_stream(
        self,
        stream_id: str,
        cursor: Optional[str] = None,
        order: str = "desc",
        limit: Optional[int] = None,
        timeout: Optional[float] = 10.0,
    ) -> Dict[str, Any]:
        """
        Consume messages from an export stream.

        Args:
            stream_id: Stream UUID or consumer key
            cursor: Starting cursor position (optional)
            order: Message order ("asc" or "desc", default: "desc")
            limit: Maximum number of messages to return (optional)
            timeout: Request timeout in seconds (default: 2.0)

        Returns:
            Dict with keys:
                - messages: List of messages
                - nextCursor: Cursor for next batch

        Example:
            ```python
            # Consume from current position
            result = client.consume_stream("abc-123")
            for msg in result['messages']:
                print(f"Identifier: {msg['displayValue']}")

            # Consume from beginning
            result = client.consume_stream(
                stream_id="abc-123",
                cursor="0",
                order="asc",
                limit=100
            )

            # Continue with next cursor
            next_result = client.consume_stream(
                stream_id="abc-123",
                cursor=result['nextCursor'],
                order="asc"
            )
            ```
        """
        url = f"{self.api_url}/consume/{stream_id}/poll"
        params = {}
        if cursor:
            params["cursor"] = cursor
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit

        # Use custom timeout for stream consumption to avoid blocking tests
        try:
            response = self.session.request(
                method="GET",
                url=url,
                params=params,
                timeout=timeout,
            )

            if response.status_code >= 400:
                self._handle_error_response(response)

            if response.status_code == 204:
                return {}

            return response.json()
        except Exception as e:
            raise ScambusAPIError(f"Request failed: {e}")

    def recover_stream(
        self,
        stream_id: str,
        ignore_checkpoint: bool = False,
        clear_stream: bool = True,
    ) -> Dict[str, Any]:
        """
        Trigger recovery/rebuild for an export stream.

        Args:
            stream_id: Stream UUID
            ignore_checkpoint: Rebuild last 24 hours instead of using checkpoint (default: False)
            clear_stream: Clear stream before rebuilding (default: True)

        Returns:
            Recovery status dict

        Example:
            ```python
            # Checkpoint-based recovery (default)
            result = client.recover_stream("abc-123")

            # 24-hour full rebuild
            result = client.recover_stream(
                stream_id="abc-123",
                ignore_checkpoint=True
            )

            # Gap-fill without clearing
            result = client.recover_stream(
                stream_id="abc-123",
                clear_stream=False
            )
            ```
        """
        params = {}
        if ignore_checkpoint:
            params["ignore_checkpoint"] = "true"
        if not clear_stream:
            params["clear_stream"] = "false"

        response = self._request("POST", f"/export-streams/{stream_id}/recover", params=params)
        return response

    def get_recovery_status(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        stream_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recent recovery history and status for all streams.

        Args:
            limit: Maximum number of recovery logs to return
            offset: Number of logs to skip for pagination
            stream_id: Filter by specific stream ID

        Returns:
            Dict with recovery logs

        Example:
            ```python
            status = client.get_recovery_status()
            for log in status.get('logs', []):
                print(f"Stream: {log['streamName']}, Status: {log.get('completedAt', 'In Progress')}")

            # Filter by stream and paginate
            stream_status = client.get_recovery_status(stream_id="stream-123", limit=10)
            ```
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if stream_id is not None:
            params["streamId"] = stream_id

        response = self._request("GET", "/redis/recovery/history", params=params if params else None)
        return response

    def get_stream_recovery_info(self, stream_id: str) -> Dict[str, Any]:
        """
        Get recovery information for a specific stream.

        Args:
            stream_id: Stream UUID

        Returns:
            Dict with recovery information

        Example:
            ```python
            info = client.get_stream_recovery_info("abc-123")
            print(f"Is Rebuilding: {info.get('isRebuilding')}")
            print(f"Last Consumed Entry: {info.get('lastConsumedJournalEntry')}")
            print(f"Entries to Replay: {info.get('journalEntriesToReplay')}")
            ```
        """
        response = self._request("GET", f"/export-streams/{stream_id}/recovery-info")
        return response

    def backfill_stream(
        self,
        stream_id: str,
        from_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Trigger backfill for an identifier-centric stream.

        Args:
            stream_id: Stream UUID
            from_date: Only backfill from this date (RFC3339 format, optional)

        Returns:
            Backfill status dict

        Example:
            ```python
            # Backfill all identifiers
            result = client.backfill_stream("abc-123")

            # Backfill from specific date
            result = client.backfill_stream(
                stream_id="abc-123",
                from_date="2025-01-01T00:00:00Z"
            )
            ```
        """
        params = {}
        if from_date:
            params["fromDate"] = from_date

        response = self._request(
            "POST", f"/export-streams/{stream_id}/backfill-identifiers", params=params
        )
        return response

    # User Methods

    def get_case_comments(self, case_id: str) -> List[CaseComment]:
        """
        Get comments for a case.

        Args:
            case_id: Case UUID

        Returns:
            List of CaseComment objects

        Example:
            ```python
            comments = client.get_case_comments("case-123")
            for comment in comments:
                print(f"{comment.content} by {comment.author_id}")
            ```
        """
        response = self._request("GET", f"/cases/{case_id}/comments")
        if isinstance(response, list):
            return [CaseComment.from_dict(c) for c in response]
        return []

    def create_case_comment(
        self,
        case_id: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> CaseComment:
        """
        Create a comment on a case.

        Args:
            case_id: Case UUID
            content: Comment content (Markdown supported)
            parent_comment_id: Optional parent comment UUID for nested replies

        Returns:
            Created CaseComment object

        Example:
            ```python
            comment = client.create_case_comment(
                "case-123",
                "This case needs more investigation"
            )

            # Reply to a comment
            reply = client.create_case_comment(
                "case-123",
                "I agree, I'll look into it",
                parent_comment_id=comment.id
            )
            ```
        """
        data = {"content": content}
        if parent_comment_id:
            data["parentCommentId"] = parent_comment_id

        response = self._request("POST", f"/cases/{case_id}/comments", json_data=data)
        return CaseComment.from_dict(response)

    def update_case_comment(self, comment_id: str, content: str) -> CaseComment:
        """
        Update a case comment.

        Args:
            comment_id: Comment UUID
            content: New content

        Returns:
            Updated CaseComment object

        Example:
            ```python
            comment = client.update_case_comment(
                "comment-123",
                "Updated comment content"
            )
            ```
        """
        response = self._request("PUT", f"/comments/{comment_id}", json_data={"content": content})
        return CaseComment.from_dict(response)

    def delete_case_comment(self, comment_id: str) -> None:
        """
        Delete a case comment.

        Args:
            comment_id: Comment UUID

        Example:
            ```python
            client.delete_case_comment("comment-123")
            ```
        """
        self._request("DELETE", f"/comments/{comment_id}")

    def get_comment_count(self, case_id: str) -> int:
        """
        Get comment count for a case.

        Args:
            case_id: Case UUID

        Returns:
            Number of comments

        Example:
            ```python
            count = client.get_comment_count("case-123")
            print(f"Case has {count} comments")
            ```
        """
        response = self._request("GET", f"/cases/{case_id}/comments/count")
        return response.get("count", 0)

    # Tag Methods

    def list_tags(self) -> List[Tag]:
        """
        List all tags.

        Returns:
            List of Tag objects

        Example:
            ```python
            tags = client.list_tags()
            for tag in tags:
                print(f"{tag.title}: {tag.tag_type}")
            ```
        """
        response = self._request("GET", "/tags")
        if isinstance(response, list):
            return [Tag.from_dict(t) for t in response]
        return []

    def get_tag(self, tag_id: str) -> Tag:
        """
        Get tag by ID.

        Args:
            tag_id: Tag UUID

        Returns:
            Tag object

        Example:
            ```python
            tag = client.get_tag("tag-123")
            print(f"Tag: {tag.title}")
            ```
        """
        response = self._request("GET", f"/tags/{tag_id}")
        return Tag.from_dict(response)

    def create_tag(
        self,
        title: str,
        tag_type: str = "valued",
        description: Optional[str] = None,
        applicable_models: Optional[List[str]] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        flows_up_to_case: bool = False,
        flows_down_to_evidence: bool = False,
        allocates_karma: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tag:
        """
        Create a tag.

        Args:
            title: Tag title
            tag_type: Tag type (boolean or valued)
            description: Tag description
            applicable_models: Models this tag applies to
            color: Optional hex color
            icon: Optional icon identifier
            flows_up_to_case: Whether tag flows up to cases
            flows_down_to_evidence: Whether tag flows down to evidence
            allocates_karma: Karma points to award
            metadata: Optional metadata dictionary for additional tracking (e.g., test_batch, environment)

        Returns:
            Created Tag object

        Example:
            ```python
            tag = client.create_tag(
                title="High Priority",
                tag_type="boolean",
                description="High priority items",
                flows_up_to_case=True
            )
            ```
        """
        data = {
            "title": title,
            "tagType": tag_type,
        }
        if description:
            data["description"] = description
        if applicable_models:
            data["applicableModels"] = applicable_models
        if color:
            data["color"] = color
        if icon:
            data["icon"] = icon
        if flows_up_to_case:
            data["flowsUpToCase"] = flows_up_to_case
        if flows_down_to_evidence:
            data["flowsDownToEvidence"] = flows_down_to_evidence
        if allocates_karma is not None:
            data["allocatesKarma"] = allocates_karma
        if metadata:
            data["metadata"] = metadata

        response = self._request("POST", "/tags", json_data=data)
        return Tag.from_dict(response)

    def update_tag(
        self,
        tag_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Tag:
        """
        Update a tag.

        Args:
            tag_id: Tag UUID
            title: New title
            description: New description
            color: New color
            icon: New icon
            active: Whether tag is active

        Returns:
            Updated Tag object

        Example:
            ```python
            tag = client.update_tag(
                "tag-123",
                description="Updated description"
            )
            ```
        """
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if color is not None:
            data["color"] = color
        if icon is not None:
            data["icon"] = icon
        if active is not None:
            data["active"] = active

        response = self._request("PUT", f"/tags/{tag_id}", json_data=data)
        return Tag.from_dict(response)

    def delete_tag(self, tag_id: str) -> None:
        """
        Delete a tag.

        Args:
            tag_id: Tag UUID

        Example:
            ```python
            client.delete_tag("tag-123")
            ```
        """
        self._request("DELETE", f"/tags/{tag_id}")

    def list_tag_values(self, tag_id: str) -> List[TagValue]:
        """
        List values for a tag.

        Args:
            tag_id: Tag UUID

        Returns:
            List of TagValue objects

        Example:
            ```python
            values = client.list_tag_values("tag-123")
            for value in values:
                print(f"{value.title}")
            ```
        """
        response = self._request("GET", f"/tags/{tag_id}/values")
        if isinstance(response, list):
            return [TagValue.from_dict(v) for v in response]
        return []

    def create_tag_value(
        self,
        tag_id: str,
        title: str,
        description: Optional[str] = None,
        order: int = 0,
    ) -> TagValue:
        """
        Create a tag value.

        Args:
            tag_id: Tag UUID
            title: Value title
            description: Value description
            order: Display order

        Returns:
            Created TagValue object

        Example:
            ```python
            value = client.create_tag_value(
                "tag-123",
                title="High",
                description="High priority",
                order=1
            )
            ```
        """
        data = {"title": title}
        if description:
            data["description"] = description
        if order:
            data["order"] = order

        response = self._request("POST", f"/tags/{tag_id}/values", json_data=data)
        return TagValue.from_dict(response)

    def update_tag_value(
        self,
        tag_id: str,
        value_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        order: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> TagValue:
        """
        Update a tag value.

        Args:
            tag_id: Tag UUID
            value_id: Tag value UUID
            title: New title
            description: New description
            order: New order
            active: Whether value is active

        Returns:
            Updated TagValue object

        Example:
            ```python
            value = client.update_tag_value(
                "tag-123",
                "value-456",
                title="Very High"
            )
            ```
        """
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if order is not None:
            data["order"] = order
        if active is not None:
            data["active"] = active

        response = self._request("PUT", f"/tags/{tag_id}/values/{value_id}", json_data=data)
        return TagValue.from_dict(response)

    def delete_tag_value(self, tag_id: str, value_id: str) -> None:
        """
        Delete a tag value.

        Args:
            tag_id: Tag UUID
            value_id: Tag value UUID

        Example:
            ```python
            client.delete_tag_value("tag-123", "value-456")
            ```
        """
        self._request("DELETE", f"/tags/{tag_id}/values/{value_id}")

    def get_effective_tags(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get effective tags for an entity.

        Args:
            entity_type: Entity type (identifier, evidence, case)
            entity_id: Entity UUID

        Returns:
            List of effective tag dictionaries

        Example:
            ```python
            tags = client.get_effective_tags("identifier", "id-123")
            for tag in tags:
                print(f"Tag: {tag['tag']['title']}")
            ```
        """
        response = self._request("GET", f"/tags/effective/{entity_type}/{entity_id}")
        if isinstance(response, list):
            return response
        return []

    def get_tag_history(self, entity_type: str, entity_id: str) -> List[JournalEntry]:
        """
        Get tag operation history for an entity.

        Args:
            entity_type: Entity type (identifier, evidence, case)
            entity_id: Entity UUID

        Returns:
            List of JournalEntry objects

        Example:
            ```python
            history = client.get_tag_history("identifier", "id-123")
            for entry in history:
                print(f"Operation at {entry.performed_at}")
            ```
        """
        response = self._request("GET", f"/tags/history/{entity_type}/{entity_id}")
        if isinstance(response, list):
            return [JournalEntry.from_dict(e) for e in response]
        return []

    # Search Methods

    def search_identifiers(
        self,
        query: Optional[str] = None,
        types: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        limit: int = 50,
    ) -> List[Identifier]:
        """
        Search identifiers.

        Args:
            query: Search query
            types: List of identifier types to filter
            min_confidence: Minimum confidence score
            max_confidence: Maximum confidence score
            limit: Maximum number of results

        Returns:
            List of Identifier objects

        Example:
            ```python
            identifiers = client.search_identifiers(
                query="example.com",
                types=["email", "phone"],
                min_confidence=0.8
            )
            ```
        """
        data = {"limit": limit}
        if query:
            data["searchQuery"] = query
        if types:
            # Backend expects "type" for a single type filter
            if len(types) == 1:
                data["type"] = types[0]
            else:
                # For multiple types, we'll just use the first one
                # Backend doesn't support multiple type filters
                data["type"] = types[0]
        if min_confidence is not None:
            data["minConfidence"] = min_confidence
        if max_confidence is not None:
            data["maxConfidence"] = max_confidence

        response = self._request("POST", "/search/identifiers", json_data=data)
        # Backend returns {data: [], nextCursor, hasMore}
        if isinstance(response, dict) and "data" in response:
            data_list = response["data"]
            if data_list is None:
                return []
            return [Identifier.from_dict(i) for i in data_list]
        # Fallback for legacy format
        if isinstance(response, list):
            return [Identifier.from_dict(i) for i in response]
        return []

    def search_cases(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Case]:
        """
        Search cases.

        Args:
            query: Search query
            status: Case status filter
            limit: Maximum number of results

        Returns:
            List of Case objects

        Example:
            ```python
            cases = client.search_cases(
                query="fraud",
                status="active"
            )
            ```
        """
        data = {"limit": limit}
        if query:
            data["query"] = query
        if status:
            data["status"] = status

        response = self._request("POST", "/search/cases", json_data=data)
        if isinstance(response, list):
            return [Case.from_dict(c) for c in response]
        return []

    # Notification Methods

    def list_notifications(
        self,
        unread_only: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Notification]:
        """
        List notifications for current user.

        Args:
            unread_only: Only return unread notifications
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip for pagination

        Returns:
            List of Notification objects

        Example:
            ```python
            notifications = client.list_notifications(unread_only=True)
            for notif in notifications:
                print(f"{notif.notification_text}")

            # With pagination
            page1 = client.list_notifications(limit=10, offset=0)
            page2 = client.list_notifications(limit=10, offset=10)
            ```
        """
        params = {}
        if unread_only:
            params["unread"] = "true"
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = self._request("GET", "/notifications", params=params)
        if isinstance(response, list):
            return [Notification.from_dict(n) for n in response]
        return []

    def get_notification(self, notification_id: str) -> Notification:
        """
        Get notification by ID.

        Args:
            notification_id: Notification UUID

        Returns:
            Notification object

        Example:
            ```python
            notification = client.get_notification("notif-123")
            print(f"Text: {notification.notification_text}")
            ```
        """
        response = self._request("GET", f"/notifications/{notification_id}")
        return Notification.from_dict(response)

    def get_unread_notification_count(self) -> int:
        """
        Get count of unread notifications.

        Returns:
            Number of unread notifications

        Example:
            ```python
            count = client.get_unread_notification_count()
            print(f"You have {count} unread notifications")
            ```
        """
        response = self._request("GET", "/notifications/unread-count")
        return response.get("count", 0)

    def mark_notification_as_read(self, notification_id: str) -> None:
        """
        Mark notification as read.

        Args:
            notification_id: Notification UUID

        Example:
            ```python
            client.mark_notification_as_read("notif-123")
            ```
        """
        self._request("POST", f"/notifications/{notification_id}/mark-read")

    def mark_all_notifications_as_read(self) -> None:
        """
        Mark all notifications as read.

        Example:
            ```python
            client.mark_all_notifications_as_read()
            ```
        """
        self._request("POST", "/notifications/mark-all-read")

    def dismiss_notification(self, notification_id: str) -> None:
        """
        Dismiss a notification.

        Args:
            notification_id: Notification UUID

        Example:
            ```python
            client.dismiss_notification("notif-123")
            ```
        """
        self._request("POST", f"/notifications/{notification_id}/dismiss")

    def dismiss_all_notifications(self) -> None:
        """
        Dismiss all notifications.

        Example:
            ```python
            client.dismiss_all_notifications()
            ```
        """
        self._request("POST", "/notifications/dismiss-all")

    # Session Methods

    def list_sessions(self) -> List[Session]:
        """
        List current user's sessions.

        Returns:
            List of Session objects

        Example:
            ```python
            sessions = client.list_sessions()
            for session in sessions:
                print(f"Session: {session.user_agent}")
            ```
        """
        response = self._request("GET", "/sessions")
        if isinstance(response, list):
            return [Session.from_dict(s) for s in response]
        return []

    def revoke_session(self, session_id: str) -> None:
        """
        Revoke a session.

        Args:
            session_id: Session UUID

        Example:
            ```python
            client.revoke_session("session-123")
            ```
        """
        self._request("POST", f"/sessions/{session_id}/revoke")

    def list_passkeys(self) -> List[Passkey]:
        """
        List current user's passkeys.

        Returns:
            List of Passkey objects

        Example:
            ```python
            passkeys = client.list_passkeys()
            for pk in passkeys:
                print(f"{pk.name}: {pk.sign_count} signatures")
            ```
        """
        response = self._request("GET", "/passkeys")
        if isinstance(response, list):
            return [Passkey.from_dict(p) for p in response]
        return []

    def delete_passkey(self, passkey_id: str) -> None:
        """
        Delete a passkey.

        Args:
            passkey_id: Passkey UUID

        Example:
            ```python
            client.delete_passkey("passkey-123")
            ```
        """
        self._request("DELETE", f"/passkeys/{passkey_id}")

    def get_2fa_status(self) -> Dict[str, Any]:
        """
        Get 2FA status for current user.

        Returns:
            Dictionary with 2FA status

        Example:
            ```python
            status = client.get_2fa_status()
            print(f"2FA enabled: {status.get('enabled')}")
            ```
        """
        response = self._request("GET", "/passkeys/2fa")
        return response

    def toggle_2fa(self, enabled: bool) -> Dict[str, Any]:
        """
        Toggle 2FA for current user.

        Args:
            enabled: Whether to enable 2FA

        Returns:
            Dictionary with updated 2FA status

        Example:
            ```python
            result = client.toggle_2fa(True)
            ```
        """
        response = self._request("POST", "/passkeys/2fa", json_data={"enabled": enabled})
        return response

    # WebSocket Methods

    def create_websocket_client(
        self, max_reconnect_attempts: int = 10, reconnect_delay: float = 1.0
    ):
        """
        Create a WebSocket client for real-time notifications and updates.

        This method creates a WebSocketClient with the same authentication
        credentials as this HTTP client.

        Args:
            max_reconnect_attempts: Maximum number of reconnection attempts (default: 10)
            reconnect_delay: Initial delay between reconnection attempts in seconds (default: 1.0)

        Returns:
            ScambusWebSocketClient instance

        Example:
            ```python
            import asyncio
            from scambus_client import ScambusClient

            # Initialize HTTP client
            client = ScambusClient(
                api_url="https://api.scambus.net/api",
                api_key_id="your-key-id",
                api_key_secret="your-secret"
            )

            # Create WebSocket client
            ws_client = client.create_websocket_client()

            # Define notification handler
            async def handle_notification(notification):
                print(f"New notification: {notification['title']}")
                print(f"Message: {notification['message']}")

            # Start listening for notifications
            asyncio.run(ws_client.listen_notifications(handle_notification))
            ```
        """
        from .websocket_client import ScambusWebSocketClient

        # Extract authentication credentials
        auth_header = None
        for key, value in self.session.headers.items():
            if key == "X-API-Key":
                # Parse API key format: "key_id:secret"
                parts = value.split(":", 1)
                if len(parts) == 2:
                    return ScambusWebSocketClient(
                        api_url=self.api_url,
                        api_key_id=parts[0],
                        api_key_secret=parts[1],
                        max_reconnect_attempts=max_reconnect_attempts,
                        reconnect_delay=reconnect_delay,
                    )
            elif key == "Authorization" and value.startswith("Bearer "):
                token = value[7:]  # Remove "Bearer " prefix
                return ScambusWebSocketClient(
                    api_url=self.api_url,
                    api_token=token,
                    max_reconnect_attempts=max_reconnect_attempts,
                    reconnect_delay=reconnect_delay,
                )

        raise ValueError("Could not extract authentication credentials from client")

    # Automation Methods

    def create_automation(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new automation identity.

        Args:
            name: Automation name
            description: Optional description
            active: Whether the automation is active (default: True)

        Returns:
            Automation object with id, name, description, etc.
        """
        body = {"name": name, "active": active}
        if description:
            body["description"] = description

        return self._request("POST", "/automations", json_data=body)

    def create_automation_api_key(
        self,
        automation_id: str,
        name: str,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new API key for an automation.

        Args:
            automation_id: Automation UUID
            name: API key name
            expires_at: Optional expiration date (ISO 8601 format)

        Returns:
            Dict with 'apiKey', 'accessKeyId', and 'secretAccessKey'.
            NOTE: accessKeyId and secretAccessKey are only returned once!
        """
        body = {"name": name}
        if expires_at:
            body["expiresAt"] = expires_at

        return self._request("POST", f"/automations/{automation_id}/api-keys", json_data=body)

    def list_automations(self) -> List[Dict[str, Any]]:
        """
        List all automations for the organization.

        Returns:
            List of automation objects
        """
        return self._request("GET", "/automations")

    def get_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Get automation details by ID.

        Args:
            automation_id: Automation UUID

        Returns:
            Automation object
        """
        return self._request("GET", f"/automations/{automation_id}")

    def list_automation_api_keys(self, automation_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for an automation.

        Args:
            automation_id: Automation UUID

        Returns:
            List of API key objects (without secrets)
        """
        return self._request("GET", f"/automations/{automation_id}/api-keys")

    def revoke_automation_api_key(self, automation_id: str, key_id: str) -> Dict[str, Any]:
        """
        Revoke an automation API key without deleting it.

        Args:
            automation_id: Automation UUID
            key_id: API key UUID

        Returns:
            Updated API key object
        """
        return self._request("POST", f"/automations/{automation_id}/api-keys/{key_id}/revoke")

    def delete_automation_api_key(self, automation_id: str, key_id: str) -> None:
        """
        Permanently delete an automation API key.

        Args:
            automation_id: Automation UUID
            key_id: API key UUID
        """
        self._request("DELETE", f"/automations/{automation_id}/api-keys/{key_id}")

    # =========================================================================
    # Report Methods - PDF Report Generation
    # =========================================================================

    def generate_identifier_report(
        self,
        identifier_ids: Optional[List[str]] = None,
        view_id: Optional[str] = None,
        include_journal_entries: bool = True,
        include_evidence: bool = False,
        sign_report: bool = False,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
    ) -> Report:
        """
        Generate a PDF report for identifiers.

        Creates a court-admissible PDF document containing identifier data with
        proper certification, chain of custody documentation, and integrity verification.

        Args:
            identifier_ids: List of identifier UUIDs to include (optional)
            view_id: View UUID to use for selecting identifiers (optional)
            include_journal_entries: Include related journal entries (default: True)
            include_evidence: Include evidence files (default: False)
            sign_report: Digitally sign the report (default: False)
            date_range_start: Filter by date range start (optional)
            date_range_end: Filter by date range end (optional)

        Returns:
            Report object with status and download information

        Raises:
            ScambusValidationError: If no identifiers found or invalid parameters
            ScambusAPIError: If report generation fails

        Example:
            # Generate report for specific identifiers
            report = client.generate_identifier_report(
                identifier_ids=["uuid-1", "uuid-2"],
                include_journal_entries=True
            )

            # Generate report from a view
            report = client.generate_identifier_report(
                view_id="my-view-uuid",
                include_evidence=True
            )

            # Wait for completion and download
            if report.is_completed:
                pdf_bytes = client.download_report(report.id)
        """
        body: Dict[str, Any] = {
            "include_journal_entries": include_journal_entries,
            "include_evidence": include_evidence,
            "sign_report": sign_report,
        }

        if identifier_ids:
            body["identifier_ids"] = identifier_ids
        if view_id:
            body["view_id"] = view_id
        if date_range_start or date_range_end:
            body["date_range"] = {}
            if date_range_start:
                body["date_range"]["start"] = date_range_start.isoformat()
            if date_range_end:
                body["date_range"]["end"] = date_range_end.isoformat()

        response = self._request("POST", "/reports/identifiers", json_data=body)
        return Report.from_dict(response)

    def generate_journal_entry_report(
        self,
        journal_entry_ids: Optional[List[str]] = None,
        view_id: Optional[str] = None,
        include_identifiers: bool = True,
        include_evidence: bool = False,
        include_parent_chain: bool = False,
        sign_report: bool = False,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
    ) -> Report:
        """
        Generate a PDF report for journal entries.

        Creates a court-admissible PDF document containing journal entry data with
        proper certification, chain of custody documentation, and integrity verification.

        Args:
            journal_entry_ids: List of journal entry UUIDs to include (optional)
            view_id: View UUID to use for selecting entries (optional)
            include_identifiers: Include related identifiers (default: True)
            include_evidence: Include evidence files (default: False)
            include_parent_chain: Include parent entries in hierarchy (default: False)
            sign_report: Digitally sign the report (default: False)
            date_range_start: Filter by date range start (optional)
            date_range_end: Filter by date range end (optional)

        Returns:
            Report object with status and download information

        Raises:
            ScambusValidationError: If no entries found or invalid parameters
            ScambusAPIError: If report generation fails

        Example:
            # Generate report for specific entries
            report = client.generate_journal_entry_report(
                journal_entry_ids=["uuid-1", "uuid-2"],
                include_identifiers=True
            )

            # Generate report from a view
            report = client.generate_journal_entry_report(
                view_id="my-journal-view-uuid",
                include_evidence=True
            )
        """
        body: Dict[str, Any] = {
            "include_identifiers": include_identifiers,
            "include_evidence": include_evidence,
            "include_parent_chain": include_parent_chain,
            "sign_report": sign_report,
        }

        if journal_entry_ids:
            body["journal_entry_ids"] = journal_entry_ids
        if view_id:
            body["view_id"] = view_id
        if date_range_start or date_range_end:
            body["date_range"] = {}
            if date_range_start:
                body["date_range"]["start"] = date_range_start.isoformat()
            if date_range_end:
                body["date_range"]["end"] = date_range_end.isoformat()

        response = self._request("POST", "/reports/journal-entries", json_data=body)
        return Report.from_dict(response)

    def generate_view_report(
        self,
        view_id: str,
        include_evidence: bool = False,
        sign_report: bool = False,
    ) -> Report:
        """
        Generate a PDF report from a saved view.

        This is a convenience method that determines the appropriate report type
        based on the view's entity_type and generates the report.

        Args:
            view_id: View UUID or alias
            include_evidence: Include evidence files (default: False)
            sign_report: Digitally sign the report (default: False)

        Returns:
            Report object with status and download information

        Raises:
            ScambusValidationError: If view not found or unsupported entity type
            ScambusAPIError: If report generation fails

        Example:
            report = client.generate_view_report("my-fraud-identifiers-view")
            if report.is_completed:
                client.download_report(report.id, "fraud_report.pdf")
        """
        # Get the view to determine entity type
        view = self.get_view(view_id)

        if view.entity_type in ("identifier", "identifiers"):
            return self.generate_identifier_report(
                view_id=view_id,
                include_journal_entries=True,
                include_evidence=include_evidence,
                sign_report=sign_report,
            )
        elif view.entity_type in ("journal", "journal_entry", "journal_entries"):
            return self.generate_journal_entry_report(
                view_id=view_id,
                include_identifiers=True,
                include_evidence=include_evidence,
                sign_report=sign_report,
            )
        else:
            raise ScambusValidationError(
                f"Unsupported view entity type for reports: {view.entity_type}. "
                "Reports are only supported for 'identifier' and 'journal' views."
            )

    def get_report_status(self, report_id: str) -> Report:
        """
        Get the status of a report.

        Use this to poll for completion of async report generation.

        Args:
            report_id: Report UUID

        Returns:
            Report object with current status

        Raises:
            ScambusNotFoundError: If report not found
            ScambusAPIError: If request fails

        Example:
            import time

            report = client.generate_identifier_report(identifier_ids=[...])
            while report.is_processing:
                time.sleep(2)
                report = client.get_report_status(report.id)

            if report.is_completed:
                client.download_report(report.id, "output.pdf")
            elif report.is_failed:
                print(f"Report failed: {report.error_message}")
        """
        response = self._request("GET", f"/reports/{report_id}/status")
        return Report.from_dict(response)

    def download_report(
        self,
        report_id: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Download a generated PDF report.

        Args:
            report_id: Report UUID
            output_path: Optional file path to save the PDF. If provided,
                        the PDF will be written to this file.

        Returns:
            PDF file content as bytes

        Raises:
            ScambusNotFoundError: If report not found
            ScambusValidationError: If report is not ready or has expired
            ScambusAPIError: If download fails

        Example:
            # Get PDF bytes
            pdf_bytes = client.download_report(report.id)

            # Save to file
            client.download_report(report.id, "fraud_report.pdf")

            # Save to path object
            from pathlib import Path
            client.download_report(report.id, Path("reports") / "output.pdf")
        """
        url = f"{self.api_url}/reports/{report_id}/download"
        response = self.session.get(url, timeout=self.timeout)

        if response.status_code == 404:
            raise ScambusNotFoundError("Report not found")
        elif response.status_code == 400:
            raise ScambusValidationError("Report is not ready for download")
        elif response.status_code == 410:
            raise ScambusValidationError("Report has expired")
        elif response.status_code >= 400:
            self._handle_error_response(response)

        pdf_bytes = response.content

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pdf_bytes)

        return pdf_bytes

    def wait_for_report(
        self,
        report_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = 300.0,
    ) -> Report:
        """
        Wait for a report to complete generation.

        Polls the report status until it's completed, failed, or timeout is reached.

        Args:
            report_id: Report UUID
            poll_interval: Seconds between status checks (default: 2.0)
            timeout: Maximum seconds to wait (default: 300.0 / 5 minutes)
                    Set to None for no timeout.

        Returns:
            Report object with final status

        Raises:
            TimeoutError: If timeout is reached before completion
            ScambusAPIError: If status check fails

        Example:
            report = client.generate_identifier_report(identifier_ids=[...])
            try:
                report = client.wait_for_report(report.id, timeout=60)
                if report.is_completed:
                    client.download_report(report.id, "output.pdf")
            except TimeoutError:
                print("Report generation timed out")
        """
        import time

        start_time = time.time()
        report = self.get_report_status(report_id)

        while report.is_processing:
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(
                        f"Report generation timed out after {timeout} seconds"
                    )

            time.sleep(poll_interval)
            report = self.get_report_status(report_id)

        return report

    # Group Methods
