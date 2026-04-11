"""
Async Scambus API client.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from ._base_client import BaseScambusClient, _to_rfc3339
from ._retry import (
    RETRY_BASE_DELAY,
    RETRY_MAX_BACKOFF,
    RETRY_THROTTLE_BASE,
    RETRYABLE_STATUS_CODES,
)
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
    ConversationContinuationDetails,
    ConversationMessage,
    DetectionDetails,
    EmailDetails,
    Evidence,
    ExportDetails,
    ExportStream,
    ExtractedIdentifier,
    FailedIdentifier,
    Identifier,
    IdentifierLookup,
    IdentifierSummary,
    IdentifierURLReference,
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
    SpecialDomainRule,
    Tag,
    TagOperationDetails,
    TagValue,
    TextConversationDetails,
    UpdateDetails,
    URLConsolidationStatus,
    View,
)
from .types import (
    FilterCriteriaInput,
    TagLookupInput,
    StreamFilterInput,
    ViewFilterInput,
    ViewSortOrderInput,
    to_dict,
    to_dict_list,
)


logger = logging.getLogger(__name__)


class AsyncScambusClient(BaseScambusClient):
    """Async client for the Scambus API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 10,
        retry_max_time: int = 300,
    ):
        super().__init__(
            api_url=api_url,
            api_key_id=api_key_id,
            api_key_secret=api_key_secret,
            api_token=api_token,
            timeout=timeout,
            max_retries=max_retries,
            retry_max_time=retry_max_time,
        )

        self._client = httpx.AsyncClient(
            headers=self._auth_headers,
            timeout=httpx.Timeout(self.timeout),
        )

    @property
    def session(self):
        """Backward-compatible alias for the HTTP client."""
        return self._client

    @session.setter
    def session(self, value):
        self._client = value

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return False

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], List[Any]]:
        """Make an API request with automatic retry on transient failures."""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        start_time = time.monotonic()
        attempt = 0

        while True:
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    data=data,
                    files=files,
                    params=params,
                    timeout=self.timeout,
                )

                # Success path
                if response.status_code < 400:
                    if response.status_code == 204:
                        return {}
                    try:
                        return response.json()
                    except ValueError as json_err:
                        preview = response.text[:200] if response.text else "(empty)"
                        raise ScambusAPIError(
                            f"Invalid JSON response from {url} "
                            f"(status {response.status_code}): {json_err}. "
                            f"Response body: {preview}"
                        )

                # Retryable HTTP errors
                if response.status_code in RETRYABLE_STATUS_CODES:
                    elapsed = time.monotonic() - start_time
                    if attempt < self.max_retries and elapsed < self.retry_max_time:
                        attempt += 1

                        retry_after = self._parse_retry_after(response)
                        if retry_after is not None:
                            delay = min(retry_after, RETRY_MAX_BACKOFF)
                        else:
                            base = (
                                RETRY_THROTTLE_BASE
                                if response.status_code == 429
                                else RETRY_BASE_DELAY
                            )
                            delay = self._compute_backoff(attempt, base, RETRY_MAX_BACKOFF)

                        remaining = self.retry_max_time - elapsed
                        delay = min(delay, remaining)

                        logger.warning(
                            "Retryable HTTP %d on %s %s (attempt %d/%d, "
                            "backoff %.1fs, %.0fs remaining)",
                            response.status_code, method, endpoint,
                            attempt, self.max_retries, delay, remaining,
                        )
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable or retries exhausted
                self._handle_error_response(response)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                elapsed = time.monotonic() - start_time

                if attempt >= self.max_retries or elapsed >= self.retry_max_time:
                    raise ScambusAPIError(
                        f"Request to {method} {endpoint} failed after "
                        f"{attempt} retries over {elapsed:.0f}s: {exc}"
                    ) from exc

                attempt += 1
                delay = self._compute_backoff(attempt, RETRY_BASE_DELAY, RETRY_MAX_BACKOFF)
                remaining = self.retry_max_time - elapsed
                delay = min(delay, remaining)

                logger.warning(
                    "Connection error on %s %s (attempt %d/%d, "
                    "backoff %.1fs, %.0fs remaining): %s",
                    method, endpoint, attempt, self.max_retries,
                    delay, remaining, exc,
                )
                await asyncio.sleep(delay)

            except httpx.HTTPError as exc:
                raise ScambusAPIError(f"Request failed: {exc}") from exc

    # ── Media Methods ─────────────────────────────────────────────────

    async def upload_media(
        self,
        file_path: Union[str, Path],
        notes: Optional[str] = None,
        journal_entry_id: Optional[str] = None,
    ) -> Media:
        """Upload a media file from a file path."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        data = {}
        if notes:
            data["notes"] = notes
        if journal_entry_id:
            data["journalEntryId"] = journal_entry_id

        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f)}
            response = await self._request("POST", "/media/upload", data=data, files=files)

        return Media.from_dict(response)

    async def upload_media_from_buffer(
        self,
        buffer: bytes,
        filename: str,
        notes: Optional[str] = None,
        journal_entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Media:
        """Upload media from a byte buffer."""
        data = {}
        if notes:
            data["notes"] = notes
        if journal_entry_id:
            data["journalEntryId"] = journal_entry_id
        if metadata:
            import json
            data["metadata"] = json.dumps(metadata)

        files = {"file": (filename, buffer)}
        response = await self._request("POST", "/media/upload", data=data, files=files)

        return Media.from_dict(response)

    async def get_media(self, media_id: str) -> Media:
        """Get media by ID."""
        response = await self._request("GET", f"/media/{media_id}")
        return Media.from_dict(response)

    # ── Journal Entry Methods ─────────────────────────────────────────

    async def create_journal_entry(
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
        is_test: bool = False,
        ai_extract: bool = False,
        retracted_identifier_ids: Optional[List[str]] = None,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
        allow_confidence_decrease: bool = False,
    ) -> JournalEntry:
        """Create a journal entry with automatic identifier resolution."""
        data = {
            "type": entry_type,
            "description": description,
        }

        if details:
            data["details"] = details
        if performed_at:
            data["performed_at"] = _to_rfc3339(performed_at)
        if case_id:
            data["case_id"] = case_id
        if identifier_lookups:
            data["identifier_lookups"] = [
                lookup.to_dict() if isinstance(lookup, IdentifierLookup) else lookup
                for lookup in identifier_lookups
            ]
        if our_identifier_lookups:
            data["our_identifier_lookups"] = [
                lookup.to_dict() if isinstance(lookup, IdentifierLookup) else lookup
                for lookup in our_identifier_lookups
            ]
        if evidence:
            data["evidence"] = evidence.to_dict() if isinstance(evidence, Evidence) else evidence
        if originator_type and originator_identifier:
            data["originator_lookup"] = {
                "type": originator_type,
                "identifier": originator_identifier,
                "create_if_not_exists": create_originator,
            }
        if parent_journal_entry_id:
            data["parent_journal_entry_id"] = parent_journal_entry_id
        if tags:
            data["tag_lookups"] = to_dict_list(tags)
        if metadata:
            data["metadata"] = metadata
        if is_test:
            data["is_test"] = is_test
        if ai_extract:
            data["ai_extract"] = True
        if retracted_identifier_ids:
            data["retracted_identifier_ids"] = retracted_identifier_ids
        if external_identifiers:
            data["external_identifiers"] = external_identifiers
        if extract_external_identifiers:
            data["extract_external_identifiers"] = True
        if allow_confidence_decrease:
            data["allow_confidence_decrease"] = True

        # Handle start_time and end_time
        if start_time:
            data["start_time"] = _to_rfc3339(start_time)
            if in_progress:
                pass
            elif end_time is None:
                data["end_time"] = _to_rfc3339(start_time)
            else:
                data["end_time"] = _to_rfc3339(end_time)
        elif end_time:
            data["end_time"] = _to_rfc3339(end_time)

        response = await self._request("POST", "/journal-entries", json_data=data)

        failed_identifiers = None
        if "failed_identifiers" in response:
            failed_identifiers = [
                FailedIdentifier.from_dict(fi) for fi in response["failed_identifiers"]
            ]

        extracted_identifiers = None
        if "extracted_identifiers" in response:
            extracted_identifiers = [
                ExtractedIdentifier.from_dict(ei)
                for ei in response["extracted_identifiers"]
            ]

        entry_id = response["id"]
        entry = await self.get_journal_entry(entry_id)

        entry._client = self
        entry.failed_identifiers = failed_identifiers
        entry.extracted_identifiers = extracted_identifiers

        return entry

    async def batch_create_journal_entries(
        self, entries: List[Dict[str, Any]]
    ) -> "BatchCreateResult":
        """Create multiple journal entries in a single request."""
        from .models import BatchCreateResult

        response = await self._request(
            "POST", "/journal-entries/batch", json_data={"entries": entries}
        )
        return BatchCreateResult.from_dict(response)

    async def create_detection(
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
        is_test: bool = False,
        performed_at: Optional[datetime] = None,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create a 'detection' type journal entry."""
        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": (
                        "screenshot" if media_list[0].mime_type.startswith("image/") else "file"
                    ),
                    "title": "Detection Evidence",
                    "description": f"Evidence for detection: {description}",
                    "source": "Automated Detection",
                    "collected_at": _to_rfc3339(datetime.now(timezone.utc)),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        details_dict = details
        if isinstance(details, DetectionDetails):
            details_dict = details.to_dict()

        return await self.create_journal_entry(
            entry_type="detection",
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
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_phone_call(
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
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create a 'phone_call' type journal entry."""
        details = PhoneCallDetails(
            direction=direction,
            recording_url=recording_url,
            transcript_url=transcript_url,
        )

        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": (
                        "recording"
                        if any(m.mime_type.startswith("audio/") for m in media_list)
                        else "file"
                    ),
                    "title": "Phone Call Evidence",
                    "description": f"Evidence for phone call: {description}",
                    "source": "Phone Call Recording",
                    "collected_at": _to_rfc3339(start_time),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return await self.create_journal_entry(
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
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_email(
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
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create an 'email' type journal entry."""
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

        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "screenshot",
                    "title": "Email Evidence",
                    "description": f"Evidence for email: {subject}",
                    "source": "Email Communication",
                    "collectedAt": _to_rfc3339(sent_at),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return await self.create_journal_entry(
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
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_text_conversation(
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
        ai_extract: bool = False,
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create a 'text_conversation' type journal entry."""
        details_obj = TextConversationDetails(
            platform=platform,
        )

        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "screenshot",
                    "title": f"{platform} Conversation Evidence",
                    "description": f"Evidence for {platform} conversation: {description}",
                    "source": f"{platform} Communication",
                    "collectedAt": _to_rfc3339(start_time),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return await self.create_journal_entry(
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
            ai_extract=ai_extract,
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_conversation_continuation(
        self,
        parent_entry: Union[str, "JournalEntry"],
        messages: List[Union[ConversationMessage, Dict[str, Any]]],
        description: str = "Conversation continuation",
        reason: Optional[str] = None,
        non_contiguous: bool = False,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        our_identifier_lookups: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        media: Optional[Union[Media, List[Media]]] = None,
        evidence: Optional[Union[Dict[str, Any], Evidence]] = None,
        case_id: Optional[str] = None,
        tags: Optional[List[TagLookupInput]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        ai_extract: bool = False,
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create a 'conversation_continuation' journal entry."""
        if not messages:
            raise ValueError("messages must not be empty")

        parent_id = parent_entry.id if isinstance(parent_entry, JournalEntry) else parent_entry

        msg_objects = []
        for msg in messages:
            if isinstance(msg, ConversationMessage):
                msg_objects.append(msg)
            else:
                msg_objects.append(ConversationMessage.from_dict(msg))

        details_obj = ConversationContinuationDetails(
            messages=msg_objects,
            reason=reason,
            non_contiguous=non_contiguous,
        )

        timestamps = [m.timestamp for m in msg_objects]
        start_time = min(timestamps) if timestamps else None
        end_time = max(timestamps) if timestamps else None

        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "screenshot",
                    "title": "Conversation Continuation Evidence",
                    "description": f"Evidence for continuation: {description}",
                    "source": "Conversation Messages",
                    "media_ids": media_ids,
                }
                if start_time:
                    evidence["collectedAt"] = _to_rfc3339(start_time)
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return await self.create_journal_entry(
            entry_type="conversation_continuation",
            description=description,
            details=details_obj.to_dict(),
            performed_at=start_time,
            parent_journal_entry_id=parent_id,
            case_id=case_id,
            identifier_lookups=identifiers,
            our_identifier_lookups=our_identifier_lookups,
            evidence=evidence,
            tags=tags,
            metadata=metadata,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
            start_time=start_time,
            end_time=end_time,
            ai_extract=ai_extract,
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_note(
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
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create a 'note' type journal entry."""
        details_dict = details
        if isinstance(details, NoteDetails):
            details_dict = details.to_dict()

        if media is not None:
            media_list = media if isinstance(media, list) else [media]
            media_ids = [m.id for m in media_list]

            if evidence is None:
                evidence = {
                    "type": "document",
                    "title": "Note Evidence",
                    "description": f"Evidence for note: {description}",
                    "source": "Note Attachment",
                    "collected_at": _to_rfc3339(performed_at or datetime.now(timezone.utc)),
                    "media_ids": media_ids,
                }
            else:
                if isinstance(evidence, Evidence):
                    evidence.media_ids.extend(media_ids)
                elif isinstance(evidence, dict):
                    if "media_ids" not in evidence:
                        evidence["media_ids"] = []
                    evidence["media_ids"].extend(media_ids)

        return await self.create_journal_entry(
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
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_import(
        self,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        case_id: Optional[str] = None,
        performed_at: Optional[datetime] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create an 'import' type journal entry."""
        return await self.create_journal_entry(
            entry_type="import",
            description=description,
            details=details,
            performed_at=performed_at or datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def create_export(
        self,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        identifiers: Optional[List[Union[Dict[str, Any], IdentifierLookup]]] = None,
        case_id: Optional[str] = None,
        performed_at: Optional[datetime] = None,
        originator_type: Optional[str] = None,
        originator_identifier: Optional[str] = None,
        create_originator: bool = False,
        is_test: bool = False,
        external_identifiers: Optional[List[Dict[str, str]]] = None,
        extract_external_identifiers: bool = False,
    ) -> JournalEntry:
        """Create an 'export' type journal entry."""
        return await self.create_journal_entry(
            entry_type="export",
            description=description,
            details=details,
            performed_at=performed_at or datetime.now(timezone.utc),
            case_id=case_id,
            identifier_lookups=identifiers,
            originator_type=originator_type,
            originator_identifier=originator_identifier,
            create_originator=create_originator,
            is_test=is_test,
            external_identifiers=external_identifiers,
            extract_external_identifiers=extract_external_identifiers,
        )

    async def get_journal_entry(self, entry_id: str) -> JournalEntry:
        """Get journal entry by ID."""
        response = await self._request("GET", f"/journal-entries/{entry_id}")

        journal_entry_data = response["journal_entry"]["journal_entry"]
        entry = JournalEntry.from_dict(journal_entry_data)
        entry._client = self
        return entry

    async def get_identifier_summary(
        self,
        entry_id: str,
        identifier_type: Optional[str] = None,
    ) -> IdentifierSummary:
        """
        Get a count of distinct identifiers attached to a journal entry and its
        descendants, grouped by type (and by subtype for payment_token /
        social_media).

        Args:
            entry_id: Journal entry UUID
            identifier_type: Optional identifier type to filter by

        Returns:
            IdentifierSummary with total, per-type counts, and per-subtype
            breakdown.
        """
        params = {}
        if identifier_type:
            params["type"] = identifier_type
        response = await self._request(
            "GET",
            f"/journal-entries/{entry_id}/identifier-summary",
            params=params or None,
        )
        return IdentifierSummary.from_dict(response)

    async def get_external_systems(self) -> List[Dict[str, str]]:
        """List registered external system plugins."""
        return await self._request("GET", "/external-systems")

    async def delete_journal_entry(self, entry_id: str) -> bool:
        """Delete a journal entry by ID."""
        await self._request("DELETE", f"/journal-entries/{entry_id}")
        return True

    async def complete_activity(
        self,
        parent_entry: Union[str, JournalEntry],
        end_time: Optional[datetime] = None,
        completion_reason: str = "manual",
        description: Optional[str] = None,
    ) -> JournalEntry:
        """Complete an in-progress activity."""
        if isinstance(parent_entry, str):
            parent_id = parent_entry
            parent = await self.get_journal_entry(parent_id)
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

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        duration_seconds = int((end_time - start_time).total_seconds())

        details = ActivityCompleteDetails(
            completion_reason=completion_reason,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
        )

        if description is None:
            description = f"Activity completed ({completion_reason})"

        return await self.create_journal_entry(
            entry_type="activity_complete",
            description=description,
            details=details.to_dict(),
            parent_journal_entry_id=parent_id,
        )

    async def list_journal_entries(
        self,
        entry_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[JournalEntry]:
        """List journal entries."""
        params = {"page": page, "limit": limit}
        if entry_type:
            params["type"] = entry_type

        response = await self._request("GET", "/journal-entries", params=params)

        if isinstance(response, dict) and "data" in response:
            return [JournalEntry.from_dict(item["journal_entry"]) for item in response["data"]]
        else:
            return []

    async def query_journal_entries(
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
        include_test: bool = False,
        filter_criteria: Optional[FilterCriteriaInput] = None,
        include_originator: bool = False,
    ) -> Dict[str, Any]:
        """Query journal entries with advanced filtering."""
        if filter_criteria is not None:
            body = to_dict(filter_criteria)
        else:
            body = {}

        body["order_by"] = order_by
        body["order_desc"] = order_desc
        body["include_identifiers"] = include_identifiers
        body["include_evidence"] = include_evidence

        if cursor:
            body["cursor"] = cursor
        if parent_journal_entry_id:
            body["parent_journal_entry_id"] = parent_journal_entry_id
        if include_children:
            body["include_children"] = include_children
        if include_originator:
            body["include_originator"] = include_originator
        if search_query:
            body["search_query"] = search_query
        if entry_type:
            body["types"] = [entry_type]
        if originator_type:
            body["originator_types"] = [originator_type]
        if originator_id:
            body["originator_ids"] = [originator_id]
        if min_confidence is not None:
            body["min_confidence"] = min_confidence
        if max_confidence is not None:
            body["max_confidence"] = max_confidence
        if include_test:
            body["is_test"] = True

        if performed_after:
            if isinstance(performed_after, datetime):
                body["performed_after"] = _to_rfc3339(performed_after)
            else:
                body["performed_after"] = performed_after

        if performed_before:
            if isinstance(performed_before, datetime):
                body["performed_before"] = _to_rfc3339(performed_before)
            else:
                body["performed_before"] = performed_before

        if details:
            body["details"] = details

        response = await self._request("POST", "/journal/query", json_data=body)

        return {
            "data": [JournalEntry.from_dict(entry) for entry in (response.get("data") or [])],
            "nextCursor": response.get("nextCursor"),
            "hasMore": response.get("hasMore", False),
            "count": response.get("count", 0),
            "estimatedTotal": response.get("estimatedTotal"),
        }

    async def create_stream_from_query(
        self,
        name: str,
        entry_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        performed_after: Optional[Union[str, datetime]] = None,
        performed_before: Optional[Union[str, datetime]] = None,
        search_query: Optional[str] = None,
    ) -> ExportStream:
        """Create a temporary export stream from query parameters."""
        from .types import ViewFilter
        import json

        filter_params = ViewFilter(
            entry_types=[entry_type] if entry_type else None,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            performed_after=(
                _to_rfc3339(performed_after)
                if isinstance(performed_after, datetime)
                else performed_after
            ),
            performed_before=(
                _to_rfc3339(performed_before)
                if isinstance(performed_before, datetime)
                else performed_before
            ),
            search_query=search_query,
        )

        data = {
            "name": name,
            "data_type": "journal_entry",
            "filter_expression": json.dumps(filter_params.to_dict()),
        }

        response = await self._request("POST", "/export-streams/temporary", json_data=data)
        return ExportStream.from_dict(response)

    async def get_in_progress_activities(self) -> List[JournalEntry]:
        """Get journal entries that are currently in progress."""
        response = await self._request("GET", "/journal-entries/in-progress")

        if isinstance(response, list):
            return [JournalEntry.from_dict(entry) for entry in response]
        return []

    # ── View Methods ──────────────────────────────────────────────────

    async def list_views(self) -> List[View]:
        """List all available views."""
        response = await self._request("GET", "/views")

        if isinstance(response, list):
            return [View.from_dict(view) for view in response]
        return []

    async def get_view(self, view_id: str) -> View:
        """Get a specific view by ID."""
        response = await self._request("GET", f"/views/{view_id}")
        return View.from_dict(response)

    async def execute_view(
        self,
        view_id: str,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a saved view query."""
        body = {}
        if cursor:
            body["cursor"] = cursor
        if limit:
            body["limit"] = limit

        response = await self._request("POST", f"/views/{view_id}/execute", json_data=body)

        return {
            "data": response.get("data") or [],
            "nextCursor": response.get("nextCursor"),
            "hasMore": response.get("hasMore", False),
            "count": response.get("count", 0),
            "entity_type": response.get("entity_type", "journal"),
        }

    async def create_view(
        self,
        name: str,
        entity_type: str,
        filter_criteria: Optional[Union[ViewFilterInput, FilterCriteriaInput]] = None,
        sort_order: Optional[ViewSortOrderInput] = None,
        description: Optional[str] = None,
        alias: Optional[str] = None,
        visibility: str = "organization",
        view_type: str = "standard",
        query_string: Optional[str] = None,
        display_settings: Optional[Dict[str, Any]] = None,
    ) -> View:
        """Create a new view (saved query)."""
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
        if query_string:
            body["query_string"] = query_string
        if display_settings:
            body["display_settings"] = display_settings

        response = await self._request("POST", "/views", json_data=body)
        return View.from_dict(response)

    async def update_view(
        self,
        view_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        filter_criteria: Optional[Union[ViewFilterInput, FilterCriteriaInput]] = None,
        sort_order: Optional[ViewSortOrderInput] = None,
        visibility: Optional[str] = None,
        query_string: Optional[str] = None,
        display_settings: Optional[Dict[str, Any]] = None,
    ) -> View:
        """Update an existing view."""
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
        if query_string is not None:
            body["query_string"] = query_string
        if display_settings is not None:
            body["display_settings"] = display_settings

        response = await self._request("PUT", f"/views/{view_id}", json_data=body)
        return View.from_dict(response)

    async def delete_view(self, view_id: str) -> None:
        """Delete a view."""
        await self._request("DELETE", f"/views/{view_id}")

    async def get_my_journal_entries_view(self) -> View:
        """Get the 'My Journal Entries' system view object."""
        response = await self._request("GET", "/views/my-journal-entries")
        return View.from_dict(response)

    async def get_my_pinboard_view(self) -> View:
        """Get the 'My Pinboard' system view object."""
        response = await self._request("GET", "/views/my-pinboard")
        return View.from_dict(response)

    async def execute_my_journal_entries(
        self, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute the 'My Journal Entries' view and return results."""
        view = await self.get_my_journal_entries_view()
        return await self.execute_view(view.id, cursor=cursor, limit=limit)

    async def execute_my_pinboard(
        self, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute the 'My Pinboard' view and return results."""
        view = await self.get_my_pinboard_view()
        return await self.execute_view(view.id, cursor=cursor, limit=limit)

    # ── Identifier Methods ────────────────────────────────────────────

    async def list_identifiers(
        self,
        identifier_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[Identifier]:
        """List identifiers."""
        params = {"page": page, "limit": limit}
        if identifier_type:
            params["type"] = identifier_type

        response = await self._request("GET", "/identifiers", params=params)

        if isinstance(response, dict) and "data" in response:
            return [Identifier.from_dict(identifier) for identifier in response["data"]]
        else:
            return []

    async def get_identifier(self, identifier_id: str) -> Identifier:
        """Get identifier by ID."""
        response = await self._request("GET", f"/identifiers/{identifier_id}")
        return Identifier.from_dict(response)

    # ── Helper Methods (non-async, no HTTP calls) ─────────────────────

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
        """Helper to create a properly formatted bank account identifier lookup."""
        import json

        bank_data = {
            "account_number": str(account),
            "routing": str(routing),
            "institution": str(institution),
        }

        if owner is not None:
            bank_data["owner"] = owner
        if owner_address is not None:
            bank_data["owner_address"] = owner_address
        if country is not None:
            bank_data["country"] = country

        result = {
            "type": "bank_account",
            "value": json.dumps(bank_data),
        }

        if confidence is not None:
            result["confidence"] = confidence

        return result

    def create_venmo_identifier(
        self,
        identifier: str,
        name: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Helper to create a properly formatted Venmo payment_token identifier lookup."""
        import json
        import re
        from urllib.parse import urlparse, parse_qs

        identifier = identifier.strip()
        venmo_data: Dict[str, Any] = {"service": "venmo"}

        if identifier.startswith("https://") or identifier.startswith("http://"):
            parsed = urlparse(identifier)
            if parsed.hostname and parsed.hostname.lower() != "venmo.com":
                raise ValueError(f"Venmo URL must be from venmo.com, got: {parsed.hostname}")
            clean_path = parsed.path.rstrip("/")
            if clean_path != "/code":
                raise ValueError(f"Venmo URL must use /code path, got: {clean_path}")
            params = parse_qs(parsed.query)
            user_ids = params.get("user_id", [])
            if not user_ids or not user_ids[0]:
                raise ValueError("Venmo URL missing user_id query parameter")
            user_id = user_ids[0]
            if not re.match(r"^\d{16,19}$", user_id):
                raise ValueError(f"Venmo user_id must be 16-19 digits, got: {user_id}")
            venmo_data["identifier"] = identifier
        elif identifier.startswith("@"):
            if not re.match(r"^@[a-zA-Z0-9_-]{5,30}$", identifier):
                raise ValueError(
                    "Invalid Venmo @username (must be 5-30 alphanumeric/hyphen/underscore characters)"
                )
            venmo_data["identifier"] = identifier
        elif re.match(r"^\d{16,19}$", identifier):
            venmo_data["identifier"] = identifier
        else:
            raise ValueError(
                "Venmo identifier must be an @username, numeric user_id (16-19 digits), "
                "or venmo.com/code QR URL"
            )

        if name is not None:
            venmo_data["name"] = name

        result: Dict[str, Any] = {
            "type": "payment_token",
            "value": json.dumps(venmo_data),
        }

        if confidence is not None:
            result["confidence"] = confidence

        return result

    def create_chime_identifier(
        self,
        chimesign: str,
        name: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Helper to create a properly formatted Chime payment_token identifier lookup."""
        import json
        import re

        chimesign = chimesign.strip()
        if not chimesign.startswith("$"):
            raise ValueError("Chime identifier must be a $ChimeSign (e.g. $JohnDoe)")
        if not re.match(r"^\$[a-zA-Z0-9_]{1,20}$", chimesign):
            raise ValueError(
                "Invalid $ChimeSign (must be $username, 1-20 alphanumeric/underscore characters)"
            )

        chime_data: Dict[str, Any] = {"service": "chime", "identifier": chimesign}
        if name is not None:
            chime_data["name"] = name

        result: Dict[str, Any] = {
            "type": "payment_token",
            "value": json.dumps(chime_data),
        }

        if confidence is not None:
            result["confidence"] = confidence

        return result

    # ── Case Methods ──────────────────────────────────────────────────

    async def list_cases(
        self,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        include_test: bool = False,
    ) -> List[Case]:
        """List cases with optional filtering."""
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if category:
            params["category"] = category
        if include_test:
            params["includeTest"] = "true"

        response = await self._request("GET", "/cases", params=params)

        if isinstance(response, dict) and "data" in response:
            return [Case.from_dict(case) for case in response["data"]]
        else:
            return []

    async def get_case(self, case_id: str) -> Case:
        """Get case by ID."""
        response = await self._request("GET", f"/cases/{case_id}")
        return Case.from_dict(response)

    async def create_case(
        self,
        title: str,
        notes: Optional[str] = None,
        status: str = "open",
        priority: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
        is_test: bool = False,
    ) -> Case:
        """Create a new case."""
        data = {
            "title": title,
            "status": status,
            "priority": priority,
        }
        if notes:
            data["notes"] = notes
        if metadata:
            data["metadata"] = metadata
        if is_test:
            data["is_test"] = is_test

        response = await self._request("POST", "/cases", json_data=data)
        return Case.from_dict(response)

    async def update_case(
        self,
        case_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        is_test: Optional[bool] = None,
    ) -> Case:
        """Update an existing case."""
        data = {}
        if title is not None:
            data["title"] = title
        if notes is not None:
            data["notes"] = notes
        if status is not None:
            data["status"] = status
        if priority is not None:
            data["priority"] = priority
        if is_test is not None:
            data["is_test"] = is_test

        if not data:
            raise ScambusValidationError("At least one field must be provided for update")

        await self._request("PUT", f"/cases/{case_id}", json_data=data)

        # Backend returns 204 No Content, so fetch the updated case
        return await self.get_case(case_id)

    async def delete_case(self, case_id: str) -> None:
        """Delete a case."""
        await self._request("DELETE", f"/cases/{case_id}")

    # ── Stream Methods ────────────────────────────────────────────────

    async def list_streams(
        self,
        active: Optional[bool] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all export streams."""
        params = {}
        if active is not None:
            params["active"] = "true" if active else "false"
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        response = await self._request("GET", "/export-streams", params=params if params else None)

        if isinstance(response, dict) and "data" in response:
            return {
                "data": [ExportStream.from_dict(s) for s in response["data"]],
                "pagination": response.get("pagination", {}),
            }
        else:
            return {"data": [], "pagination": {}}

    async def get_stream(self, stream_id: str) -> ExportStream:
        """Get export stream by ID."""
        response = await self._request("GET", f"/export-streams/{stream_id}")
        return ExportStream.from_dict(response)

    @staticmethod
    def build_stream_filter(*args, **kwargs) -> str:
        """Build a JSONPath filter expression for stream filtering. Delegates to sync client."""
        from .client import ScambusClient
        return ScambusClient.build_stream_filter(*args, **kwargs)

    async def create_stream(
        self,
        name: str,
        data_type: str = "journal_entry",
        identifier_types: Optional[Union[str, List[str]]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        is_active: bool = True,
        retention_days: Optional[int] = None,
        backfill_historical: bool = False,
        backfill_from_date: Optional[str] = None,
        filter_expression: Optional[str] = None,
        filter_criteria: Optional[FilterCriteriaInput] = None,
        description: Optional[str] = None,
        include_originator: bool = False,
        include_journal_entries: bool = False,
        batch_size: Optional[int] = None,
        rate_limit_per_minute: Optional[int] = None,
        shared_org_ids: Optional[List[str]] = None,
    ) -> ExportStream:
        """Create a new export stream."""
        data: Dict[str, Any] = {
            "name": name,
            "data_type": data_type,
            "backfill_historical": backfill_historical,
        }

        if filter_criteria is not None:
            data["filter_criteria"] = to_dict(filter_criteria)
        else:
            fc: Dict[str, Any] = {}
            if identifier_types:
                if isinstance(identifier_types, str):
                    identifier_types = [identifier_types]
                fc["identifier_type"] = identifier_types[0]
            if min_confidence is not None:
                fc["min_confidence"] = min_confidence
            if max_confidence is not None:
                fc["max_confidence"] = max_confidence
            if fc:
                data["filter_criteria"] = fc

        if description:
            data["description"] = description
        if retention_days is not None:
            data["retention_days"] = retention_days
        if backfill_from_date:
            data["backfill_from_date"] = backfill_from_date
        if include_originator:
            data["include_originator"] = include_originator
        if include_journal_entries:
            data["include_journal_entries"] = include_journal_entries
        if batch_size is not None:
            data["batch_size"] = batch_size
        if rate_limit_per_minute is not None:
            data["rate_limit_per_minute"] = rate_limit_per_minute
        if shared_org_ids:
            data["shared_org_ids"] = shared_org_ids
        if filter_expression:
            data["filter_expression"] = filter_expression

        response = await self._request("POST", "/export-streams", json_data=data)
        return ExportStream.from_dict(response)

    async def create_temporary_stream(
        self,
        data_type: str = "identifier",
        identifier_types: Optional[Union[str, List[str]]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        filter_expression: Optional[str] = None,
        name: Optional[str] = None,
        view_id: Optional[str] = None,
        filter_criteria: Optional[FilterCriteriaInput] = None,
        include_originator: bool = False,
        include_journal_entries: bool = False,
        batch_size: Optional[int] = None,
    ) -> ExportStream:
        """Create a temporary export stream."""
        data: Dict[str, Any] = {
            "data_type": data_type,
        }

        if filter_criteria is not None:
            data["filter_criteria"] = to_dict(filter_criteria)
        else:
            fc: Dict[str, Any] = {}
            if identifier_types:
                if isinstance(identifier_types, str):
                    identifier_types = [identifier_types]
                fc["identifier_type"] = identifier_types[0]
            if min_confidence is not None:
                fc["min_confidence"] = min_confidence
            if max_confidence is not None:
                fc["max_confidence"] = max_confidence
            if fc:
                data["filter_criteria"] = fc

        if name:
            data["name"] = name
        if view_id:
            data["view_id"] = view_id
        if include_originator:
            data["include_originator"] = include_originator
        if include_journal_entries:
            data["include_journal_entries"] = include_journal_entries
        if batch_size is not None:
            data["batch_size"] = batch_size
        if filter_expression:
            data["filter_expression"] = filter_expression

        response = await self._request("POST", "/export-streams/temporary", json_data=data)
        return ExportStream.from_dict(response)

    async def delete_stream(self, stream_id: str) -> None:
        """Delete an export stream."""
        await self._request("DELETE", f"/export-streams/{stream_id}")

    async def consume_stream(
        self,
        stream_id: str,
        cursor: Optional[str] = None,
        order: str = "asc",
        limit: Optional[int] = None,
        include_test: Optional[bool] = None,
        timeout: Optional[float] = 10.0,
    ) -> Dict[str, Any]:
        """Consume messages from an export stream via HTTP polling."""
        url = f"{self.api_url}/consume/{stream_id}/poll"
        params = {}
        if cursor:
            params["cursor"] = cursor
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        if include_test is not None:
            params["include_test"] = str(include_test).lower()

        try:
            response = await self._client.request(
                method="GET",
                url=url,
                params=params,
                timeout=timeout,
            )

            if response.status_code >= 400:
                self._handle_error_response(response)

            if response.status_code == 204:
                return {
                    "messages": [],
                    "next_cursor": None,
                    "has_more": False,
                    "nextCursor": None,
                    "hasMore": False,
                }

            data = response.json()

            next_cursor = data.get("next_cursor") if "next_cursor" in data else data.get("nextCursor")
            has_more = data.get("has_more", data.get("hasMore", False))
            return {
                "messages": data.get("messages", []),
                "next_cursor": next_cursor,
                "has_more": has_more,
                "nextCursor": next_cursor,
                "hasMore": has_more,
            }
        except ScambusAPIError:
            raise
        except Exception as e:
            raise ScambusAPIError(f"Request failed: {e}")

    async def get_stream_info(
        self,
        consumer_key: str,
        timeout: Optional[float] = 10.0,
    ) -> Dict[str, Any]:
        """Get information about a stream using its consumer key."""
        url = f"{self.api_url}/consume/{consumer_key}/info"

        try:
            response = await self._client.request(
                method="GET",
                url=url,
                timeout=timeout,
            )

            if response.status_code >= 400:
                self._handle_error_response(response)

            return response.json()
        except ScambusAPIError:
            raise
        except Exception as e:
            raise ScambusAPIError(f"Request failed: {e}")

    async def recover_stream(
        self,
        stream_id: str,
        ignore_checkpoint: bool = False,
        clear_stream: bool = True,
    ) -> Dict[str, Any]:
        """Trigger recovery/rebuild for an export stream."""
        params = {}
        if ignore_checkpoint:
            params["ignore_checkpoint"] = "true"
        if not clear_stream:
            params["clear_stream"] = "false"

        response = await self._request("POST", f"/export-streams/{stream_id}/recover", params=params)
        return response

    async def get_recovery_status(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        stream_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get recent recovery history and status for all streams."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if stream_id is not None:
            params["streamId"] = stream_id

        response = await self._request(
            "GET", "/redis/recovery/history", params=params if params else None
        )
        return response

    async def get_stream_recovery_info(self, stream_id: str) -> Dict[str, Any]:
        """Get recovery information for a specific stream."""
        response = await self._request("GET", f"/export-streams/{stream_id}/recovery-info")
        return response

    async def backfill_stream(
        self,
        stream_id: str,
        from_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger backfill for an identifier-centric stream."""
        params = {}
        if from_date:
            params["fromDate"] = from_date

        response = await self._request(
            "POST", f"/export-streams/{stream_id}/backfill-identifiers", params=params
        )
        return response

    # ── File Export Methods ────────────────────────────────────────────

    async def create_file_export(
        self,
        source_type: str,
        entity_type: str,
        format: str = "csv",
        source_id: Optional[str] = None,
        filter_criteria: Optional[FilterCriteriaInput] = None,
        name: Optional[str] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        date_range_start: Optional[str] = None,
        date_range_end: Optional[str] = None,
        include_ours: bool = False,
        format_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a file export (CSV, JSON, etc.) from a view or search."""
        body: Dict[str, Any] = {
            "source_type": source_type,
            "entity_type": entity_type,
            "format": format,
        }

        if source_id:
            body["source_id"] = source_id
        if filter_criteria is not None:
            body["filter_criteria"] = to_dict(filter_criteria)
        if name:
            body["name"] = name
        if columns:
            body["columns"] = columns
        if limit is not None:
            body["limit"] = limit
        if date_range_start:
            body["date_range_start"] = date_range_start
        if date_range_end:
            body["date_range_end"] = date_range_end
        if include_ours:
            body["include_ours"] = include_ours
        if format_options:
            body["format_options"] = format_options

        return await self._request("POST", "/file-exports", json_data=body)

    async def list_file_exports(self) -> List[Dict[str, Any]]:
        """List file exports."""
        response = await self._request("GET", "/file-exports")
        if isinstance(response, list):
            return response
        return []

    async def get_file_export(self, export_id: str) -> Dict[str, Any]:
        """Get a file export by ID."""
        return await self._request("GET", f"/file-exports/{export_id}")

    async def download_file_export(self, export_id: str, output_path: str) -> None:
        """Download a completed file export to a local file."""
        async with self._client.stream(
            "GET",
            f"{self.api_url}/file-exports/{export_id}/download",
            timeout=self.timeout,
        ) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    async def rename_file_export(self, export_id: str, name: str) -> Dict[str, Any]:
        """Rename a file export."""
        return await self._request("PATCH", f"/file-exports/{export_id}/rename", json_data={"name": name})

    async def delete_file_export(self, export_id: str) -> None:
        """Delete a file export."""
        await self._request("DELETE", f"/file-exports/{export_id}")

    # ── Case Comment Methods ──────────────────────────────────────────

    async def get_case_comments(self, case_id: str) -> List[CaseComment]:
        """Get comments for a case."""
        response = await self._request("GET", f"/cases/{case_id}/comments")
        if isinstance(response, list):
            return [CaseComment.from_dict(c) for c in response]
        return []

    async def create_case_comment(
        self,
        case_id: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> CaseComment:
        """Create a comment on a case."""
        data = {"content": content}
        if parent_comment_id:
            data["parentCommentId"] = parent_comment_id

        response = await self._request("POST", f"/cases/{case_id}/comments", json_data=data)
        return CaseComment.from_dict(response)

    async def update_case_comment(self, comment_id: str, content: str) -> CaseComment:
        """Update a case comment."""
        response = await self._request("PUT", f"/comments/{comment_id}", json_data={"content": content})
        return CaseComment.from_dict(response)

    async def delete_case_comment(self, comment_id: str) -> None:
        """Delete a case comment."""
        await self._request("DELETE", f"/comments/{comment_id}")

    async def get_comment_count(self, case_id: str) -> int:
        """Get comment count for a case."""
        response = await self._request("GET", f"/cases/{case_id}/comments/count")
        return response.get("count", 0)

    # ── Tag Methods ───────────────────────────────────────────────────

    async def list_tags(self) -> List[Tag]:
        """List all tags."""
        response = await self._request("GET", "/tags")
        if isinstance(response, list):
            return [Tag.from_dict(t) for t in response]
        return []

    async def get_tag(self, tag_id: str) -> Tag:
        """Get tag by ID."""
        response = await self._request("GET", f"/tags/{tag_id}")
        return Tag.from_dict(response)

    async def create_tag(
        self,
        title: str,
        tag_type: str = "valued",
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        is_global: bool = False,
        flow_up: bool = True,
        flow_down: bool = True,
        allow_dynamic_values: bool = False,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        allocates_karma: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tag_values: Optional[List[Dict[str, Any]]] = None,
    ) -> Tag:
        """Create a tag."""
        data: Dict[str, Any] = {
            "title": title,
            "tag_type": tag_type,
            "flow_up": flow_up,
            "flow_down": flow_down,
            "allow_dynamic_values": allow_dynamic_values,
        }
        if description:
            data["description"] = description
        if aliases:
            data["aliases"] = aliases
        if is_global:
            data["is_global"] = is_global
        if color:
            data["color"] = color
        if icon:
            data["icon"] = icon
        if allocates_karma is not None:
            data["allocates_karma"] = allocates_karma
        if metadata:
            data["metadata"] = metadata
        if tag_values:
            data["tag_values"] = tag_values

        response = await self._request("POST", "/tags", json_data=data)
        return Tag.from_dict(response)

    async def update_tag(
        self,
        tag_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        is_global: Optional[bool] = None,
        flow_up: Optional[bool] = None,
        flow_down: Optional[bool] = None,
        allow_dynamic_values: Optional[bool] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        active: Optional[bool] = None,
        tag_values: Optional[List[Dict[str, Any]]] = None,
    ) -> Tag:
        """Update a tag."""
        data: Dict[str, Any] = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if aliases is not None:
            data["aliases"] = aliases
        if is_global is not None:
            data["is_global"] = is_global
        if flow_up is not None:
            data["flow_up"] = flow_up
        if flow_down is not None:
            data["flow_down"] = flow_down
        if allow_dynamic_values is not None:
            data["allow_dynamic_values"] = allow_dynamic_values
        if color is not None:
            data["color"] = color
        if icon is not None:
            data["icon"] = icon
        if active is not None:
            data["active"] = active
        if tag_values is not None:
            data["tag_values"] = tag_values

        response = await self._request("PUT", f"/tags/{tag_id}", json_data=data)
        return Tag.from_dict(response)

    async def delete_tag(self, tag_id: str) -> None:
        """Delete a tag."""
        await self._request("DELETE", f"/tags/{tag_id}")

    async def list_tag_values(self, tag_id: str) -> List[TagValue]:
        """List values for a tag."""
        response = await self._request("GET", f"/tags/{tag_id}/values")
        if isinstance(response, list):
            return [TagValue.from_dict(v) for v in response]
        return []

    async def create_tag_value(
        self,
        tag_id: str,
        title: str,
        description: Optional[str] = None,
        order: int = 0,
    ) -> TagValue:
        """Create a tag value."""
        data = {"title": title}
        if description:
            data["description"] = description
        if order:
            data["order"] = order

        response = await self._request("POST", f"/tags/{tag_id}/values", json_data=data)
        return TagValue.from_dict(response)

    async def update_tag_value(
        self,
        tag_id: str,
        value_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        order: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> TagValue:
        """Update a tag value."""
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if order is not None:
            data["order"] = order
        if active is not None:
            data["active"] = active

        response = await self._request("PUT", f"/tags/{tag_id}/values/{value_id}", json_data=data)
        return TagValue.from_dict(response)

    async def delete_tag_value(self, tag_id: str, value_id: str) -> None:
        """Delete a tag value."""
        await self._request("DELETE", f"/tags/{tag_id}/values/{value_id}")

    async def get_effective_tags(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get effective tags for an entity."""
        response = await self._request("GET", f"/tags/effective/{entity_type}/{entity_id}")
        if isinstance(response, list):
            return response
        return []

    async def get_tag_history(self, entity_type: str, entity_id: str) -> List[JournalEntry]:
        """Get tag operation history for an entity."""
        response = await self._request("GET", f"/tags/history/{entity_type}/{entity_id}")
        if isinstance(response, list):
            return [JournalEntry.from_dict(e) for e in response]
        return []

    # ── Search Methods ────────────────────────────────────────────────

    async def search_identifiers(
        self,
        query: Optional[str] = None,
        types: Optional[List[str]] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        limit: int = 100,
        include_test: bool = False,
        filter_criteria: Optional[FilterCriteriaInput] = None,
        cursor: Optional[str] = None,
        include_journal_entries: bool = False,
    ) -> Dict[str, Any]:
        """Search identifiers with filtering and cursor-based pagination."""
        if filter_criteria is not None:
            data = to_dict(filter_criteria)
        else:
            data = {}

        data["limit"] = limit
        if query:
            data["search_query"] = query
        if types:
            if len(types) == 1:
                data["type"] = types[0]
            else:
                data["types"] = types
        if min_confidence is not None:
            data["min_confidence"] = min_confidence
        if max_confidence is not None:
            data["max_confidence"] = max_confidence
        if include_test:
            data["is_test"] = True
        if cursor:
            data["cursor"] = cursor
        if include_journal_entries:
            data["include_journal_entries"] = include_journal_entries

        response = await self._request("POST", "/search/identifiers", json_data=data)

        if isinstance(response, dict) and "data" in response:
            data_list = response.get("data") or []
            return {
                "data": [Identifier.from_dict(i) for i in data_list],
                "nextCursor": response.get("nextCursor"),
                "hasMore": response.get("hasMore", False),
                "estimatedTotal": response.get("estimatedTotal"),
            }
        if isinstance(response, list):
            return {
                "data": [Identifier.from_dict(i) for i in response],
                "nextCursor": None,
                "hasMore": False,
                "estimatedTotal": None,
            }
        return {"data": [], "nextCursor": None, "hasMore": False, "estimatedTotal": None}

    async def search_cases(
        self,
        query: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Case]:
        """Search cases."""
        data = {"limit": limit}
        if query:
            data["query"] = query
        if status:
            data["status"] = status

        response = await self._request("POST", "/search/cases", json_data=data)
        if isinstance(response, list):
            return [Case.from_dict(c) for c in response]
        return []

    # ── Notification Methods ──────────────────────────────────────────

    async def list_notifications(
        self,
        unread_only: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Notification]:
        """List notifications for current user."""
        params = {}
        if unread_only:
            params["unread"] = "true"
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        response = await self._request("GET", "/notifications", params=params)
        if isinstance(response, list):
            return [Notification.from_dict(n) for n in response]
        return []

    async def get_notification(self, notification_id: str) -> Notification:
        """Get notification by ID."""
        response = await self._request("GET", f"/notifications/{notification_id}")
        return Notification.from_dict(response)

    async def get_unread_notification_count(self) -> int:
        """Get count of unread notifications."""
        response = await self._request("GET", "/notifications/unread-count")
        return response.get("count", 0)

    async def mark_notification_as_read(self, notification_id: str) -> None:
        """Mark notification as read."""
        await self._request("POST", f"/notifications/{notification_id}/mark-read")

    async def mark_all_notifications_as_read(self) -> None:
        """Mark all notifications as read."""
        await self._request("POST", "/notifications/mark-all-read")

    async def dismiss_notification(self, notification_id: str) -> None:
        """Dismiss a notification."""
        await self._request("POST", f"/notifications/{notification_id}/dismiss")

    async def dismiss_all_notifications(self) -> None:
        """Dismiss all notifications."""
        await self._request("POST", "/notifications/dismiss-all")

    # ── Session Methods ───────────────────────────────────────────────

    async def list_sessions(self) -> List[Session]:
        """List current user's sessions."""
        response = await self._request("GET", "/sessions")
        if isinstance(response, list):
            return [Session.from_dict(s) for s in response]
        return []

    async def revoke_session(self, session_id: str) -> None:
        """Revoke a session."""
        await self._request("POST", f"/sessions/{session_id}/revoke")

    async def list_passkeys(self) -> List[Passkey]:
        """List current user's passkeys."""
        response = await self._request("GET", "/passkeys")
        if isinstance(response, list):
            return [Passkey.from_dict(p) for p in response]
        return []

    async def delete_passkey(self, passkey_id: str) -> None:
        """Delete a passkey."""
        await self._request("DELETE", f"/passkeys/{passkey_id}")

    async def get_2fa_status(self) -> Dict[str, Any]:
        """Get 2FA status for current user."""
        response = await self._request("GET", "/passkeys/2fa")
        return response

    async def toggle_2fa(self, enabled: bool) -> Dict[str, Any]:
        """Toggle 2FA for current user."""
        response = await self._request("POST", "/passkeys/2fa", json_data={"enabled": enabled})
        return response

    # ── WebSocket Methods ─────────────────────────────────────────────

    def create_websocket_client(
        self, max_reconnect_attempts: int = 10, reconnect_delay: float = 1.0
    ):
        """Create a WebSocket client for real-time notifications and updates."""
        from .websocket_client import ScambusWebSocketClient

        auth_header = None
        for key, value in self._auth_headers.items():
            if key == "X-API-Key":
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
                token = value[7:]
                return ScambusWebSocketClient(
                    api_url=self.api_url,
                    api_token=token,
                    max_reconnect_attempts=max_reconnect_attempts,
                    reconnect_delay=reconnect_delay,
                )

        raise ValueError("Could not extract authentication credentials from client")

    # ── Automation Methods ────────────────────────────────────────────

    async def create_automation(
        self,
        name: str,
        description: Optional[str] = None,
        active: bool = True,
    ) -> Dict[str, Any]:
        """Create a new automation identity."""
        body = {"name": name, "active": active}
        if description:
            body["description"] = description

        return await self._request("POST", "/automations", json_data=body)

    async def create_automation_api_key(
        self,
        automation_id: str,
        name: str,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new API key for an automation."""
        body = {"name": name}
        if expires_at:
            body["expiresAt"] = expires_at

        return await self._request("POST", f"/automations/{automation_id}/api-keys", json_data=body)

    async def list_automations(self) -> List[Dict[str, Any]]:
        """List all automations for the organization."""
        return await self._request("GET", "/automations")

    async def get_automation(self, automation_id: str) -> Dict[str, Any]:
        """Get automation details by ID."""
        return await self._request("GET", f"/automations/{automation_id}")

    async def list_automation_api_keys(self, automation_id: str) -> List[Dict[str, Any]]:
        """List all API keys for an automation."""
        return await self._request("GET", f"/automations/{automation_id}/api-keys")

    async def revoke_automation_api_key(self, automation_id: str, key_id: str) -> Dict[str, Any]:
        """Revoke an automation API key without deleting it."""
        return await self._request("POST", f"/automations/{automation_id}/api-keys/{key_id}/revoke")

    async def delete_automation_api_key(self, automation_id: str, key_id: str) -> None:
        """Permanently delete an automation API key."""
        await self._request("DELETE", f"/automations/{automation_id}/api-keys/{key_id}")

    # ── Report Methods ────────────────────────────────────────────────

    async def generate_identifier_report(
        self,
        identifier_ids: Optional[List[str]] = None,
        view_id: Optional[str] = None,
        include_journal_entries: bool = True,
        include_evidence: bool = False,
        sign_report: bool = False,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
    ) -> Report:
        """Generate a PDF report for identifiers."""
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
                body["date_range"]["start"] = _to_rfc3339(date_range_start)
            if date_range_end:
                body["date_range"]["end"] = _to_rfc3339(date_range_end)

        response = await self._request("POST", "/reports/identifiers", json_data=body)
        return Report.from_dict(response)

    async def generate_journal_entry_report(
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
        """Generate a PDF report for journal entries."""
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
                body["date_range"]["start"] = _to_rfc3339(date_range_start)
            if date_range_end:
                body["date_range"]["end"] = _to_rfc3339(date_range_end)

        response = await self._request("POST", "/reports/journal-entries", json_data=body)
        return Report.from_dict(response)

    async def generate_view_report(
        self,
        view_id: str,
        include_evidence: bool = False,
        sign_report: bool = False,
    ) -> Report:
        """Generate a PDF report from a saved view."""
        view = await self.get_view(view_id)

        if view.entity_type in ("identifier", "identifiers"):
            return await self.generate_identifier_report(
                view_id=view_id,
                include_journal_entries=True,
                include_evidence=include_evidence,
                sign_report=sign_report,
            )
        elif view.entity_type in ("journal", "journal_entry", "journal_entries"):
            return await self.generate_journal_entry_report(
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

    async def get_report_status(self, report_id: str) -> Report:
        """Get the status of a report."""
        response = await self._request("GET", f"/reports/{report_id}/status")
        return Report.from_dict(response)

    async def download_report(
        self,
        report_id: str,
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """Download a generated PDF report."""
        url = f"{self.api_url}/reports/{report_id}/download"
        response = await self._client.get(url, timeout=self.timeout)

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

    async def wait_for_report(
        self,
        report_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = 300.0,
    ) -> Report:
        """Wait for a report to complete generation."""
        start_time = time.time()
        report = await self.get_report_status(report_id)

        while report.is_processing:
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(f"Report generation timed out after {timeout} seconds")

            await asyncio.sleep(poll_interval)
            report = await self.get_report_status(report_id)

        return report

    # ── URL Reference Methods ─────────────────────────────────────────

    async def get_url_references(
        self,
        identifier_id: str,
        page: int = 1,
        page_size: int = 25,
        sort: str = "last_seen_at",
        order: str = "desc",
    ) -> Dict[str, Any]:
        """Get URL references for a URL-type identifier."""
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "order": order,
        }
        response = await self._request(
            "GET", f"/identifiers/{identifier_id}/url-references", params=params
        )
        if response.get("url_references"):
            response["url_references"] = [
                IdentifierURLReference.from_dict(r)
                for r in response["url_references"]
            ]
        else:
            response["url_references"] = []
        return response

    # ── Special Domain Rule Methods ───────────────────────────────────

    async def list_special_domain_rules(
        self,
        category: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> List[SpecialDomainRule]:
        """List special domain rules."""
        params: Dict[str, Any] = {}
        if category is not None:
            params["category"] = category
        if active is not None:
            params["active"] = "true" if active else "false"
        response = await self._request("GET", "/admin/special-domain-rules", params=params)
        if isinstance(response, list):
            return [SpecialDomainRule.from_dict(r) for r in response]
        return []

    async def create_special_domain_rule(
        self,
        domain: str,
        category: str,
        path_depth: int = 1,
        strip_query: bool = True,
        strip_fragment: bool = True,
    ) -> SpecialDomainRule:
        """Create a new special domain rule."""
        data = {
            "domain": domain,
            "category": category,
            "path_depth": path_depth,
            "strip_query": strip_query,
            "strip_fragment": strip_fragment,
        }
        response = await self._request("POST", "/admin/special-domain-rules", json_data=data)
        return SpecialDomainRule.from_dict(response)

    async def update_special_domain_rule(
        self,
        rule_id: str,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        path_depth: Optional[int] = None,
        strip_query: Optional[bool] = None,
        strip_fragment: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> SpecialDomainRule:
        """Update an existing special domain rule."""
        data: Dict[str, Any] = {}
        if domain is not None:
            data["domain"] = domain
        if category is not None:
            data["category"] = category
        if path_depth is not None:
            data["path_depth"] = path_depth
        if strip_query is not None:
            data["strip_query"] = strip_query
        if strip_fragment is not None:
            data["strip_fragment"] = strip_fragment
        if is_active is not None:
            data["is_active"] = is_active
        response = await self._request(
            "PUT", f"/admin/special-domain-rules/{rule_id}", json_data=data
        )
        return SpecialDomainRule.from_dict(response)

    async def delete_special_domain_rule(self, rule_id: str) -> None:
        """Delete a special domain rule."""
        await self._request("DELETE", f"/admin/special-domain-rules/{rule_id}")

    # ── URL Consolidation Methods ─────────────────────────────────────

    async def start_url_consolidation(self) -> URLConsolidationStatus:
        """Start the URL consolidation background job."""
        response = await self._request("POST", "/admin/url-consolidation/start")
        return URLConsolidationStatus.from_dict(response)

    async def get_url_consolidation_status(self) -> URLConsolidationStatus:
        """Get the current URL consolidation job status."""
        response = await self._request("GET", "/admin/url-consolidation/status")
        return URLConsolidationStatus.from_dict(response)

    async def cancel_url_consolidation(self) -> Dict[str, Any]:
        """Cancel a running URL consolidation job."""
        return await self._request("POST", "/admin/url-consolidation/cancel")
