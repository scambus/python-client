"""
Data models for the Scambus API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class IdentifierLookup:
    """
    Identifier lookup for automatic validation and creation.

    Attributes:
        type: Type of identifier (phone, email, bank_account, crypto_wallet, social_media, zelle)
        value: Identifier value in standard format
        confidence: Confidence score (0.0 to 1.0)
        label: Contextual label (e.g., "from", "to", "sender")
        ref: Local reference ID for message-level identifier tracking in conversations
    """

    type: str
    value: str
    confidence: Optional[float] = None
    label: Optional[str] = None
    ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {"type": self.type, "value": self.value}
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.label is not None:
            data["label"] = self.label
        if self.ref is not None:
            data["ref"] = self.ref
        return data


@dataclass
class Identifier:
    """
    Identifier from API response.

    Attributes:
        id: Identifier UUID
        type: Type of identifier
        display_value: Human-readable display value
        confidence: Confidence score (0.0 to 1.0)
        data: Type-specific data
    """

    id: str
    type: str
    display_value: str
    confidence: Optional[float] = None
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Identifier":
        """Create from API response dictionary."""
        # Extract confidence score - backend always returns {"score": 0.95}
        confidence_data = data.get("confidence")
        confidence = confidence_data.get("score") if confidence_data else None

        return cls(
            id=data["id"],
            type=data["type"],
            display_value=data.get("display_value", ""),
            confidence=confidence,
            data=data.get("data"),
            created_at=cls._parse_datetime(data.get("created_at")),
            updated_at=cls._parse_datetime(data.get("updated_at")),
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string, handling both with and without timezone."""
        if not dt_str:
            return None
        # Replace Z with +00:00 for proper parsing
        dt_str = dt_str.replace("Z", "+00:00")
        # If no timezone info, assume UTC
        if "+" not in dt_str and dt_str.count(":") >= 2:
            dt_str = dt_str + "+00:00"
        return datetime.fromisoformat(dt_str)


@dataclass
class Evidence:
    """
    Evidence attached to a journal entry (read-only from API).
    Evidence is created through journal entries, not directly.

    Attributes:
        id: Evidence UUID
        type: Type of evidence (screenshot, recording, document, etc.)
        title: Evidence title
        description: Detailed description
        source: Where/how evidence was obtained
        collected_at: When evidence was collected
        media_ids: List of media IDs attached
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    type: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    collected_at: Optional[datetime] = None
    media_ids: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """Create Evidence from API response."""
        return cls(
            id=data["id"],
            type=data["type"],
            title=data["title"],
            description=data.get("description"),
            source=data.get("source"),
            collected_at=Identifier._parse_datetime(data.get("collected_at")),
            media_ids=data.get("media_ids", []),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
        )


@dataclass
class Media:
    """
    Media file from API response.

    Attributes:
        id: Media UUID
        type: Storage type (s3, external_url)
        file_name: File name
        mime_type: MIME type
        file_size: File size in bytes
        notes: Optional notes
        uploaded_at: Upload timestamp
    """

    id: str
    type: str
    file_name: str
    mime_type: str
    file_size: int
    notes: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    journal_entry_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Media":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            file_name=data.get("file_name", ""),
            mime_type=data.get("mime_type", ""),
            file_size=data.get("file_size", 0),
            notes=data.get("notes"),
            uploaded_at=Identifier._parse_datetime(data.get("uploaded_at")),
            journal_entry_id=data.get("journal_entry_id"),
        )


@dataclass
class PhoneCallDetails:
    """
    Details for a phone call journal entry.

    Note: start_time and end_time are now set at the top level of the JournalEntry,
    not in the details object.

    Attributes:
        direction: Call direction ("inbound" or "outbound")
        recording_url: Optional URL to call recording
        transcript_url: Optional URL to call transcript
    """

    direction: str
    recording_url: Optional[str] = None
    transcript_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "direction": self.direction,
        }
        if self.recording_url:
            data["recordingUrl"] = self.recording_url
        if self.transcript_url:
            data["transcriptUrl"] = self.transcript_url
        return data


@dataclass
class EmailDetails:
    """
    Details for an email journal entry.

    Attributes:
        direction: Email direction ("inbound" or "outbound")
        subject: Email subject line
        sent_at: When the email was sent
        body: Plain text body (optional)
        html_body: HTML body (optional)
        message_id: Email message ID (optional)
        headers: Email headers as key-value pairs (optional)
        attachments: List of attachment filenames (optional)
    """

    direction: str
    subject: str
    sent_at: datetime
    body: Optional[str] = None
    html_body: Optional[str] = None
    message_id: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    attachments: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "direction": self.direction,
            "subject": self.subject,
            "sentAt": self.sent_at.isoformat(),
        }
        if self.body:
            data["body"] = self.body
        if self.html_body:
            data["htmlBody"] = self.html_body
        if self.message_id:
            data["messageId"] = self.message_id
        if self.headers:
            data["headers"] = self.headers
        if self.attachments:
            data["attachments"] = self.attachments
        return data


@dataclass
class CustodyEvent:
    """
    Chain of custody event for evidence tracking.

    Attributes:
        timestamp: When the event occurred
        event: Event type ("collected", "transferred", "uploaded", "verified")
        method: How the event was performed
        actor: Who performed the event (optional)
        notes: Additional notes (optional)
    """

    timestamp: datetime
    event: str
    method: str
    actor: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "timestamp": self.timestamp.isoformat(),
            "event": self.event,
            "method": self.method,
        }
        if self.actor:
            data["actor"] = self.actor
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class MessageIdentifierRef:
    """
    Reference to an identifier within a conversation message.

    Attributes:
        ref: Local reference ID matching an IdentifierLookup's ref field
        field: Where the identifier appears ("body", "subject", "headers")
        position: Byte position in the field (UTF-8 byte offset)
        length: Byte length of the matched text (UTF-8 byte count)
    """

    ref: str
    field: str = "body"
    position: Optional[int] = None
    length: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "ref": self.ref,
            "field": self.field,
        }
        if self.position is not None:
            data["position"] = self.position
        if self.length is not None:
            data["length"] = self.length
        return data


@dataclass
class MessageAttachment:
    """
    Attachment on a conversation message.

    Attributes:
        filename: Name of the file
        content_type: MIME type
        size_bytes: File size in bytes (optional)
        url: URL to the attachment (optional)
        media_id: Reference to uploaded media (optional)
    """

    filename: str
    content_type: str
    size_bytes: Optional[int] = None
    url: Optional[str] = None
    media_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "filename": self.filename,
            "content_type": self.content_type,
        }
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        if self.url:
            data["url"] = self.url
        if self.media_id:
            data["media_id"] = self.media_id
        return data


@dataclass
class ConversationMessage:
    """
    A single message in a text conversation.

    Attributes:
        index: Absolute position in the full conversation (0-based)
        message_id: Platform-specific message ID
        timestamp: When the message was sent
        body: Plain text message body (required)
        is_outgoing: True if our side sent it, False if their side (required)
        sender_ref: Reference to identifier lookup for the sender (optional)
        sender_display_name: Fallback display name for sender (optional)
        identifier_refs: List of identifier references in this message (optional)
        attachments: List of attachments (optional)
        timezone: Timezone string (optional)
        body_html: HTML body for email (optional)
        subject: Subject line for email (optional)
        is_deleted: Whether message was deleted (optional)
        is_edited: Whether message was edited (optional)
        delivery_status: Delivery status ("sent", "delivered", "read", "failed") (optional)
        delivery_timestamp: When message was delivered (optional)
        read_timestamp: When message was read (optional)
        in_reply_to: Message ID this replies to (optional)
        headers: Email headers (optional)
        platform_metadata: Platform-specific data (optional)
    """

    index: int
    message_id: str
    timestamp: datetime
    body: str
    is_outgoing: bool = False
    sender_ref: Optional[str] = None
    sender_display_name: Optional[str] = None
    identifier_refs: Optional[List[MessageIdentifierRef]] = None
    attachments: Optional[List[MessageAttachment]] = None
    timezone: Optional[str] = None
    body_html: Optional[str] = None
    subject: Optional[str] = None
    is_deleted: bool = False
    is_edited: bool = False
    delivery_status: Optional[str] = None
    delivery_timestamp: Optional[datetime] = None
    read_timestamp: Optional[datetime] = None
    in_reply_to: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    platform_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "index": self.index,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "body": self.body,
            "is_outgoing": self.is_outgoing,
        }
        if self.sender_ref:
            data["sender_ref"] = self.sender_ref
        if self.sender_display_name:
            data["sender_display_name"] = self.sender_display_name
        if self.identifier_refs:
            data["identifier_refs"] = [ref.to_dict() for ref in self.identifier_refs]
        if self.attachments:
            data["attachments"] = [att.to_dict() for att in self.attachments]
        if self.timezone:
            data["timezone"] = self.timezone
        if self.body_html:
            data["body_html"] = self.body_html
        if self.subject:
            data["subject"] = self.subject
        if self.is_deleted:
            data["is_deleted"] = self.is_deleted
        if self.is_edited:
            data["is_edited"] = self.is_edited
        if self.delivery_status:
            data["delivery_status"] = self.delivery_status
        if self.delivery_timestamp:
            data["delivery_timestamp"] = self.delivery_timestamp.isoformat()
        if self.read_timestamp:
            data["read_timestamp"] = self.read_timestamp.isoformat()
        if self.in_reply_to:
            data["in_reply_to"] = self.in_reply_to
        if self.headers:
            data["headers"] = self.headers
        if self.platform_metadata:
            data["platform_metadata"] = self.platform_metadata
        return data


@dataclass
class TextConversationDetails:
    """
    Details for a text_conversation journal entry.

    Can be used for simple entries (just platform) or entries with
    full metadata. Messages can be added via child conversation_continuation entries.

    Attributes:
        platform: Messaging platform (e.g., "sms", "whatsapp", "telegram", "signal", "email")
        conversation_type: Type of conversation ("individual" or "group") (optional)
        conversation_id: Platform-specific thread/conversation ID (optional)
        first_message_at: Timestamp of the first message (optional)
        last_message_at: Timestamp of the last message (optional)
        source_type: How the conversation was collected ("export", "screenshot", "api", "manual_entry") (optional)
        subject: Subject line for email or group name (optional)
        participant_count: Number of participants (optional)
        export_format: Format of exported data ("json", "mbox", "eml", "txt") (optional)
        collection_method: How data was collected ("user_upload", "api_sync", "screenshot_ocr") (optional)
        chain_of_custody: List of custody events for tracking (optional)
        platform_metadata: Platform-specific data (optional)

    Example (simple):
        ```python
        details = TextConversationDetails(platform="whatsapp")
        ```

    Example (with full metadata):
        ```python
        details = TextConversationDetails(
            platform="whatsapp",
            conversation_type="individual",
            conversation_id="chat_123456",
            first_message_at=datetime(2025, 1, 1, 10, 0, 0),
            last_message_at=datetime(2025, 1, 1, 11, 30, 0),
            source_type="export",
            export_format="json",
            collection_method="user_upload",
        )
        ```
    """

    platform: str
    conversation_type: Optional[str] = None
    conversation_id: Optional[str] = None
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    source_type: Optional[str] = None
    subject: Optional[str] = None
    participant_count: Optional[int] = None
    export_format: Optional[str] = None
    collection_method: Optional[str] = None
    chain_of_custody: Optional[List[CustodyEvent]] = None
    platform_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "platform": self.platform,
        }
        if self.conversation_type:
            data["conversation_type"] = self.conversation_type
        if self.conversation_id:
            data["conversation_id"] = self.conversation_id
        if self.first_message_at:
            data["first_message_at"] = self.first_message_at.isoformat()
        if self.last_message_at:
            data["last_message_at"] = self.last_message_at.isoformat()
        if self.source_type:
            data["source_type"] = self.source_type
        if self.subject:
            data["subject"] = self.subject
        if self.participant_count is not None:
            data["participant_count"] = self.participant_count
        if self.export_format:
            data["export_format"] = self.export_format
        if self.collection_method:
            data["collection_method"] = self.collection_method
        if self.chain_of_custody:
            data["chain_of_custody"] = [event.to_dict() for event in self.chain_of_custody]
        if self.platform_metadata:
            data["platform_metadata"] = self.platform_metadata
        return data


@dataclass
class ConversationContinuationDetails:
    """
    Details for a conversation_continuation journal entry (child entry with messages).

    This is a child entry of a text_conversation or email entry that contains
    the actual messages. Multiple continuation entries can be created to add
    messages to a conversation.

    Attributes:
        messages: List of messages in this continuation
        reason: Why this continuation was created (e.g., "initial import", "new messages")

    Example:
        ```python
        messages = [
            ConversationMessage(
                index=0,
                message_id="msg_001",
                timestamp=datetime(2025, 1, 1, 10, 0, 0),
                body="Hello, is this tech support?",
                sender_ref="scammer",
            ),
            ConversationMessage(
                index=1,
                message_id="msg_002",
                timestamp=datetime(2025, 1, 1, 10, 1, 0),
                body="Yes, how can I help you?",
                sender_ref="victim",
            ),
        ]

        details = ConversationContinuationDetails(
            messages=messages,
            reason="initial import"
        )
        ```
    """

    messages: List[ConversationMessage]
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "messages": [msg.to_dict() for msg in self.messages],
        }
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass
class DetectionDetails:
    """
    Details for a detection journal entry.

    Attributes:
        category: Detection category (e.g., "phishing", "scam", "malware")
        detected_at: When the detection occurred
        confidence: Confidence score (0.0 to 1.0, optional)
        details: Additional detection details (optional)
    """

    category: str
    detected_at: datetime
    confidence: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "category": self.category,
            "detectedAt": self.detected_at.isoformat(),
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.details:
            data["details"] = self.details
        return data


@dataclass
class ImportDetails:
    """
    Details for an import journal entry.

    Attributes:
        source: Source of the imported data (e.g., "csv_file", "api", "manual_entry")
        record_count: Number of records imported
        imported_at: When the import occurred
        file_name: Name of imported file (optional)
        notes: Additional notes about the import (optional)
    """

    source: str
    record_count: int
    imported_at: datetime
    file_name: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "source": self.source,
            "recordCount": self.record_count,
            "importedAt": self.imported_at.isoformat(),
        }
        if self.file_name:
            data["fileName"] = self.file_name
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class ExportDetails:
    """
    Details for an export journal entry.

    Attributes:
        destination: Export destination (e.g., "csv_file", "api", "email")
        record_count: Number of records exported
        exported_at: When the export occurred
        file_name: Name of exported file (optional)
        notes: Additional notes about the export (optional)
    """

    destination: str
    record_count: int
    exported_at: datetime
    file_name: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "destination": self.destination,
            "recordCount": self.record_count,
            "exportedAt": self.exported_at.isoformat(),
        }
        if self.file_name:
            data["fileName"] = self.file_name
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class ValidationDetails:
    """
    Details for a validation journal entry.

    Attributes:
        validation_type: Type of validation performed (e.g., "manual_review", "automated_check")
        result: Validation result (e.g., "confirmed", "rejected", "needs_review")
        validated_at: When the validation occurred
        confidence: Confidence score after validation (0.0 to 1.0, optional)
        notes: Additional notes about the validation (optional)
    """

    validation_type: str
    result: str
    validated_at: datetime
    confidence: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "validationType": self.validation_type,
            "result": self.result,
            "validatedAt": self.validated_at.isoformat(),
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class ContactDetails:
    """
    Details for contact attempt/success journal entries.

    Attributes:
        method: Contact method (e.g., "phone", "email", "in_person")
        direction: Contact direction ("inbound" or "outbound")
        contacted_at: When the contact occurred
        duration: Duration in seconds (optional)
        outcome: Outcome of the contact (e.g., "answered", "no_answer", "voicemail", optional)
        notes: Additional notes about the contact (optional)
    """

    method: str
    direction: str
    contacted_at: datetime
    duration: Optional[int] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "method": self.method,
            "direction": self.direction,
            "contactedAt": self.contacted_at.isoformat(),
        }
        if self.duration is not None:
            data["duration"] = self.duration
        if self.outcome:
            data["outcome"] = self.outcome
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class ResearchDetails:
    """
    Details for a research journal entry.

    Attributes:
        topic: Research topic or subject
        sources: List of sources consulted (optional)
        findings: Summary of findings (optional)
        researched_at: When the research was performed
        confidence: Confidence in research findings (0.0 to 1.0, optional)
    """

    topic: str
    researched_at: datetime
    sources: Optional[List[str]] = None
    findings: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "topic": self.topic,
            "researchedAt": self.researched_at.isoformat(),
        }
        if self.sources:
            data["sources"] = self.sources
        if self.findings:
            data["findings"] = self.findings
        if self.confidence is not None:
            data["confidence"] = self.confidence
        return data


@dataclass
class AnalysisDetails:
    """
    Details for an analysis journal entry.

    Attributes:
        analysis_type: Type of analysis performed (e.g., "pattern_analysis", "risk_assessment")
        findings: Analysis findings or conclusions
        analyzed_at: When the analysis was performed
        confidence: Confidence in analysis (0.0 to 1.0, optional)
        metrics: Analysis metrics or scores (optional)
    """

    analysis_type: str
    findings: str
    analyzed_at: datetime
    confidence: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "analysisType": self.analysis_type,
            "findings": self.findings,
            "analyzedAt": self.analyzed_at.isoformat(),
        }
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.metrics:
            data["metrics"] = self.metrics
        return data


@dataclass
class ActionDetails:
    """
    Details for an action_taken journal entry.

    Attributes:
        action_type: Type of action taken (e.g., "blocked_number", "reported_to_authorities", "updated_case")
        taken_at: When the action was taken
        outcome: Outcome or result of the action (optional)
        notes: Additional notes about the action (optional)
    """

    action_type: str
    taken_at: datetime
    outcome: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "actionType": self.action_type,
            "takenAt": self.taken_at.isoformat(),
        }
        if self.outcome:
            data["outcome"] = self.outcome
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class ObservationDetails:
    """
    Details for an observation journal entry.

    Attributes:
        observation_type: Type of observation (e.g., "behavioral_pattern", "system_anomaly")
        observed_at: When the observation was made
        details: Detailed description of what was observed
        significance: Significance level (e.g., "low", "medium", "high", optional)
    """

    observation_type: str
    observed_at: datetime
    details: str
    significance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "observationType": self.observation_type,
            "observedAt": self.observed_at.isoformat(),
            "details": self.details,
        }
        if self.significance:
            data["significance"] = self.significance
        return data


@dataclass
class NoteDetails:
    """
    Details for a note journal entry.

    Attributes:
        content: Note content
        category: Note category (e.g., "general", "important", "followup", optional)
        noted_at: When the note was created
    """

    content: str
    noted_at: datetime
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "content": self.content,
            "notedAt": self.noted_at.isoformat(),
        }
        if self.category:
            data["category"] = self.category
        return data


@dataclass
class UpdateDetails:
    """
    Details for an update journal entry.

    Attributes:
        update_type: Type of update (e.g., "status_change", "information_added")
        updated_at: When the update occurred
        changes: Description of changes made
        previous_value: Previous value before update (optional)
        new_value: New value after update (optional)
    """

    update_type: str
    updated_at: datetime
    changes: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "updateType": self.update_type,
            "updatedAt": self.updated_at.isoformat(),
            "changes": self.changes,
        }
        if self.previous_value:
            data["previousValue"] = self.previous_value
        if self.new_value:
            data["newValue"] = self.new_value
        return data


@dataclass
class ActivityCompleteDetails:
    """
    Details for an activity_complete journal entry.

    This is used to mark an in-progress activity as complete.
    The activity_complete entry is a child entry that references the parent activity.

    Attributes:
        completion_reason: Reason for completion ("manual" or "timeout_6h")
        start_time: When the activity started (copied from parent)
        end_time: When the activity completed
        duration_seconds: Duration of the activity in seconds

    Example:
        ```python
        # Complete an in-progress activity
        details = ActivityCompleteDetails(
            completion_reason="manual",
            start_time=activity.start_time,
            end_time=datetime.now(),
            duration_seconds=3600
        )

        entry = client.create_journal_entry(
            entry_type="activity_complete",
            description="Activity manually completed",
            details=details.to_dict(),
            parent_journal_entry_id=activity.id
        )
        ```
    """

    completion_reason: str  # "manual" | "timeout_6h"
    start_time: datetime
    end_time: datetime
    duration_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        return {
            "completionReason": self.completion_reason,
            "startTime": self.start_time.isoformat(),
            "endTime": self.end_time.isoformat(),
            "durationSeconds": self.duration_seconds,
        }


@dataclass
class TagOperationDetails:
    """
    Details for a tag_operation journal entry.

    Tags are attached to journal entries and automatically flow:
    - DOWN to identifiers and evidence linked to the journal entry
    - UP to cases that contain the journal entry

    This is determined by the tag's configuration, not by the tag operation itself.

    Attributes:
        operation: Operation type ("add" or "remove")
        tag_id: UUID of the tag being applied
        tag_value_id: UUID of the tag value for valued tags (optional)
        reason: Human-readable explanation for the operation (optional)
        notes: Additional notes about this tag application (optional)

    Example:
        ```python
        # Apply a "Verified Scam" tag to a journal entry
        tag_details = TagOperationDetails(
            operation="add",
            tag_id="uuid-of-verified-scam-tag",
            reason="Manual verification by staff"
        )

        # Create journal entry with tag (tag flows to linked identifiers/evidence automatically)
        entry = client.create_journal_entry(
            entry_type="validation",
            description="Staff verified this report",
            parent_journal_entry_id=original_report_id,
            identifier_lookups=[{"type": "phone", "value": "+15551234567"}],
            tags=[{"tagId": tag_details.tag_id}]
        )
        ```
    """

    operation: str  # "add" | "remove"
    tag_id: str
    tag_value_id: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "operation": self.operation,
            "tagId": self.tag_id,
        }
        if self.tag_value_id:
            data["tagValueId"] = self.tag_value_id
        if self.reason:
            data["reason"] = self.reason
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass
class IdentifierConfidenceUpdate:
    """
    Represents a confidence update for a single identifier.

    Attributes:
        identifier_id: UUID of the identifier
        previous_score: Previous confidence score (0.0-1.0)
        new_score: New confidence score (0.0-1.0)
        reason: Explanation for the change (optional)
    """

    identifier_id: str
    previous_score: float
    new_score: float
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "identifierId": self.identifier_id,
            "previousScore": self.previous_score,
            "newScore": self.new_score,
        }
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass
class ConfidenceOperationDetails:
    """
    Details for a confidence_operation journal entry.

    Attributes:
        identifiers: List of identifier confidence updates
        reason: Human-readable explanation for the operation (optional)
        metadata: Additional context (optional)
    """

    identifiers: List[IdentifierConfidenceUpdate]
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "identifiers": [
                (
                    id_update.to_dict()
                    if isinstance(id_update, IdentifierConfidenceUpdate)
                    else id_update
                )
                for id_update in self.identifiers
            ],
        }
        if self.reason:
            data["reason"] = self.reason
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass
class JournalEntry:
    """
    Journal entry from API response.

    Attributes:
        id: Journal entry UUID
        type: Entry type (detection, phone_call, email, etc.)
        description: Brief description
        details: Type-specific details
        performed_at: When the action/event occurred
        created_at: When entry was created
        identifiers: List of linked identifiers
        start_time: When the activity started (optional)
        end_time: When the activity ended (optional)
        _client: Internal reference to ScambusClient for calling complete()
        _raw_data: Original API response data with all fields
    """

    id: str
    type: str
    description: str
    details: Optional[Dict[str, Any]] = None
    performed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    identifiers: List[Identifier] = field(default_factory=list)
    evidence: Optional[List[Dict[str, Any]]] = None
    case_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    _client: Optional[Any] = field(default=None, repr=False)
    _raw_data: Optional[Dict[str, Any]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns the original API response data with all fields preserved,
        ensuring datetime fields are properly serialized to ISO format.
        """
        if self._raw_data:
            # Return the complete API response, serializing datetime fields
            data = dict(self._raw_data)

            # Ensure datetime fields are serialized to ISO format
            for key in ['performed_at', 'created_at', 'updated_at', 'start_time', 'end_time', 'signed_at']:
                if key in data and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()

            # Handle nested datetime in relationships
            if 'parent_journal_entry' in data and data['parent_journal_entry']:
                if isinstance(data['parent_journal_entry'], dict):
                    for key in ['performed_at', 'created_at', 'updated_at']:
                        if key in data['parent_journal_entry'] and isinstance(data['parent_journal_entry'][key], datetime):
                            data['parent_journal_entry'][key] = data['parent_journal_entry'][key].isoformat()

            return data

        # Fallback to basic fields if no raw data
        data = {
            "id": self.id,
            "type": self.type,
            "description": self.description,
        }
        if self.details:
            data["details"] = self.details
        if self.performed_at:
            data["performed_at"] = self.performed_at.isoformat()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        if self.identifiers:
            data["identifiers"] = [i.to_dict() for i in self.identifiers]
        if self.evidence:
            data["evidence"] = self.evidence
        if self.case_id:
            data["case_id"] = self.case_id
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalEntry":
        """Create from API response dictionary."""
        identifiers = []
        if "identifiers" in data and data["identifiers"]:
            identifiers = [Identifier.from_dict(i) for i in data["identifiers"]]

        entry = cls(
            id=data["id"],
            type=data.get("type", "unknown"),  # Backend may not always return type
            description=data.get("description", ""),
            details=data.get("details"),
            performed_at=Identifier._parse_datetime(data.get("performed_at")),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
            identifiers=identifiers,
            evidence=data.get("evidence"),
            case_id=data.get("case_id"),
            start_time=Identifier._parse_datetime(data.get("start_time")),
            end_time=Identifier._parse_datetime(data.get("end_time")),
        )

        # Store the complete raw response for to_dict()
        entry._raw_data = data

        return entry

    def complete(
        self,
        end_time: Optional[datetime] = None,
        completion_reason: str = "manual",
        description: Optional[str] = None,
    ) -> "JournalEntry":
        """
        Complete this in-progress activity.

        Requires that this JournalEntry was created by a ScambusClient instance.
        Creates an activity_complete journal entry linked to this entry.

        Args:
            end_time: When the activity completed (defaults to now)
            completion_reason: Reason for completion ("manual" or "timeout_6h")
            description: Optional description for the completion entry

        Returns:
            The created activity_complete JournalEntry

        Raises:
            ValueError: If this entry was not created via a ScambusClient

        Example:
            ```python
            # Create in-progress activity
            entry = client.create_journal_entry(
                entry_type="note",
                description="Reviewing case files",
                start_time=datetime.now(),
                in_progress=True
            )

            # Complete it later
            completed = entry.complete()

            # Or with custom parameters
            completed = entry.complete(
                end_time=datetime.now(),
                completion_reason="manual",
                description="Finished reviewing all files"
            )
            ```
        """
        if not self._client:
            raise ValueError(
                "Cannot complete entry: no client reference. "
                "Entry must be created via ScambusClient."
            )
        return self._client.complete_activity(
            parent_entry=self,
            end_time=end_time,
            completion_reason=completion_reason,
            description=description,
        )


@dataclass
class Case:
    """
    Case from API response.

    Attributes:
        id: Case UUID
        title: Case title
        notes: Case investigation notes (markdown supported)
        status: Case status (open, investigating, closed)
        priority: Case priority (low, medium, high, critical)
        created_at: When case was created
        updated_at: When case was last updated
        created_by: User who created the case
    """

    id: str
    title: str
    notes: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            notes=data.get("notes"),
            status=data.get("status"),
            priority=data.get("priority"),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
            created_by=data.get("created_by"),
        )


@dataclass
class ExportStream:
    """
    Export stream from API response.

    Attributes:
        id: Stream UUID
        name: Stream name
        data_type: Stream data type (journal_entry, identifier)
        identifier_types: List of identifier types to filter
        min_confidence: Minimum confidence score filter
        max_confidence: Maximum confidence score filter
        is_active: Whether stream is active
        consumer_key: Consumer key for streaming
        retention_days: Days to retain data
        created_at: When stream was created
        updated_at: When stream was last updated
    """

    id: str
    name: str
    data_type: str = "journal_entry"
    identifier_types: List[str] = field(default_factory=list)
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    is_active: bool = True
    consumer_key: Optional[str] = None
    retention_days: int = 30
    filter_expression: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportStream":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            data_type=data.get("data_type", "journal_entry"),
            identifier_types=data.get("identifier_types", []),
            min_confidence=data.get("min_confidence", 0.0),
            max_confidence=data.get("max_confidence", 1.0),
            is_active=data.get("is_active", True),
            consumer_key=data.get("consumer_key"),
            retention_days=data.get("retention_days", 30),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
        )


@dataclass
class CaseComment:
    """
    Case comment from API response.

    Attributes:
        id: Comment UUID
        case_id: Case UUID
        parent_comment_id: Parent comment UUID for nested replies
        author_id: Author user UUID
        content: Markdown content
        is_reaction: Whether this is a reaction
        reaction: Emoji if this is a reaction
        edited: Whether comment was edited
        deleted: Whether comment was soft-deleted
        created_at: When comment was created
        updated_at: When comment was updated
        deleted_at: When comment was deleted
    """

    id: str
    case_id: str
    author_id: str
    content: str
    is_reaction: bool = False
    reaction: Optional[str] = None
    edited: bool = False
    deleted: bool = False
    parent_comment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseComment":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            case_id=data["case_id"],
            author_id=data["author_id"],
            content=data.get("content", ""),
            is_reaction=data.get("is_reaction", False),
            reaction=data.get("reaction"),
            edited=data.get("edited", False),
            deleted=data.get("deleted", False),
            parent_comment_id=data.get("parent_comment_id"),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
            deleted_at=Identifier._parse_datetime(data.get("deleted_at")),
        )


@dataclass
class Tag:
    """
    Tag from API response.

    Attributes:
        id: Tag UUID
        title: Tag title
        description: Tag description
        tag_type: Tag type (boolean or valued)
        applicable_models: Models this tag can be applied to
        color: Optional hex color for UI
        icon: Optional icon identifier
        active: Whether tag is active
        is_system: Whether this is a system tag
        flows_up_to_case: Tag flows up to cases
        flows_down_to_evidence: Tag flows down to evidence
        allocates_karma: Karma points awarded
        owner_org_id: Organization that owns this tag
        created_at: When tag was created
        updated_at: When tag was updated
    """

    id: str
    title: str
    tag_type: str = "valued"
    description: Optional[str] = None
    applicable_models: List[str] = field(default_factory=list)
    color: Optional[str] = None
    icon: Optional[str] = None
    active: bool = True
    is_system: bool = False
    flows_up_to_case: bool = False
    flows_down_to_evidence: bool = False
    allocates_karma: Optional[int] = None
    owner_org_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tag":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            tag_type=data.get("tag_type", "valued"),
            description=data.get("description"),
            applicable_models=data.get("applicable_models", []),
            color=data.get("color"),
            icon=data.get("icon"),
            active=data.get("active", True),
            is_system=data.get("is_system", False),
            flows_up_to_case=data.get("flows_up_to_case", False),
            flows_down_to_evidence=data.get("flows_down_to_evidence", False),
            allocates_karma=data.get("allocates_karma"),
            owner_org_id=data.get("owner_org_id"),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
        )


@dataclass
class TagValue:
    """
    Tag value from API response.

    Attributes:
        id: Tag value UUID
        tag_id: Parent tag UUID
        title: Value title
        description: Value description
        order: Display order
        active: Whether value is active
        created_at: When value was created
        updated_at: When value was updated
    """

    id: str
    tag_id: str
    title: str
    description: Optional[str] = None
    order: int = 0
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagValue":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            tag_id=data["tag_id"],
            title=data["title"],
            description=data.get("description"),
            order=data.get("order", 0),
            active=data.get("active", True),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
        )


@dataclass
class Notification:
    """
    User notification from API response.

    Attributes:
        id: Notification UUID
        user_id: User UUID
        timestamp: Notification timestamp
        notification_text: Notification text
        service: Service name
        link: Optional router link
        read: Whether notification was read
        dismissed: Whether notification was dismissed
        icon: Optional Carbon icon name
        severity: Notification severity (info, success, warning, error)
        entity_type: Optional entity type
        entity_id: Optional entity UUID
        created_at: When notification was created
        updated_at: When notification was updated
    """

    id: str
    user_id: str
    timestamp: datetime
    notification_text: str
    service: str
    read: bool = False
    dismissed: bool = False
    link: Optional[str] = None
    icon: Optional[str] = None
    severity: str = "info"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Notification":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            timestamp=Identifier._parse_datetime(data["timestamp"]) or datetime.now(),
            notification_text=data.get("notification_text", ""),
            service=data.get("service", ""),
            read=data.get("read", False),
            dismissed=data.get("dismissed", False),
            link=data.get("link"),
            icon=data.get("icon"),
            severity=data.get("severity", "info"),
            entity_type=data.get("entity_type"),
            entity_id=data.get("entity_id"),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
        )


@dataclass
class Session:
    """
    User session from API response.

    Attributes:
        id: Session UUID
        jti: JWT ID
        user_id: User UUID
        user_type: User type (internal or external)
        clerk_user_id: Clerk user ID
        ip_address: Client IP address
        user_agent: Client user agent
        expires_at: Session expiration
        revoked_at: When session was revoked
        revoked_by: User UUID who revoked it
        revoke_reason: Revocation reason
        created_at: When session was created
    """

    id: str
    jti: str
    user_id: str
    user_type: str
    clerk_user_id: str
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revoke_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            jti=data["jti"],
            user_id=data["user_id"],
            user_type=data.get("user_type", ""),
            clerk_user_id=data.get("clerk_user_id", ""),
            expires_at=Identifier._parse_datetime(data["expires_at"]) or datetime.now(),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            revoked_at=Identifier._parse_datetime(data.get("revoked_at")),
            revoked_by=data.get("revoked_by"),
            revoke_reason=data.get("revoke_reason"),
            created_at=Identifier._parse_datetime(data.get("created_at")),
        )


@dataclass
class Passkey:
    """
    User passkey from API response.

    Attributes:
        id: Passkey UUID
        user_id: User UUID
        name: Passkey name
        sign_count: Signature counter
        transports: Supported transports
        backup_eligible: Whether backup eligible
        backup_state: Backup state
        created_at: When passkey was created
        updated_at: When passkey was updated
        last_used_at: When passkey was last used
    """

    id: str
    user_id: str
    name: str
    sign_count: int = 0
    transports: List[str] = field(default_factory=list)
    backup_eligible: bool = False
    backup_state: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Passkey":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            name=data.get("name", ""),
            sign_count=data.get("sign_count", 0),
            transports=data.get("transports", []),
            backup_eligible=data.get("backup_eligible", False),
            backup_state=data.get("backup_state", False),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
            last_used_at=Identifier._parse_datetime(data.get("last_used_at")),
        )


@dataclass
class View:
    """
    View (saved query) from API response.

    Attributes:
        id: View UUID
        name: View name
        description: View description (optional)
        alias: View alias for shortcuts (e.g., "my-journal-entries")
        entity_type: Type of entities queried ("cases", "identifiers", "evidence", "journal")
        filter_criteria: Saved filter/query criteria as dict
        sort_order: Sort order configuration as dict
        is_system: Whether this is a system view
        visibility: View visibility ("private", "organization", "public")
        view_type: View type ("standard", "journal_entry")
        created_at: Creation timestamp
        updated_at: Last update timestamp
        created_by: User who created the view
        organization_id: Organization ID
    """

    id: str
    name: str
    entity_type: str
    visibility: str = "organization"
    view_type: str = "standard"
    description: Optional[str] = None
    alias: Optional[str] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    sort_order: Optional[Dict[str, Any]] = None
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    organization_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "View":
        """Create from API response dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=data["entity_type"],
            visibility=data.get("visibility", "organization"),
            view_type=data.get("view_type", "standard"),
            description=data.get("description"),
            alias=data.get("alias"),
            filter_criteria=data.get("filter_criteria"),
            sort_order=data.get("sort_order"),
            is_system=data.get("is_system", False),
            created_at=Identifier._parse_datetime(data.get("created_at")),
            updated_at=Identifier._parse_datetime(data.get("updated_at")),
            created_by=data.get("created_by"),
            organization_id=data.get("organization_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        data = {
            "name": self.name,
            "entity_type": self.entity_type,
            "visibility": self.visibility,
            "view_type": self.view_type,
        }
        if self.description:
            data["description"] = self.description
        if self.alias:
            data["alias"] = self.alias
        if self.filter_criteria:
            data["filter_criteria"] = self.filter_criteria
        if self.sort_order:
            data["sort_order"] = self.sort_order
        return data
