"""
Scambus Python Client Library

Official Python client for Scambus - submit scam reports and subscribe to data streams.

This library enables you to:
- Submit scam reports via journal entries (phone calls, emails, text messages, detections)
- Search for identifiers, cases, and journal entries
- Create and consume export streams for real-time data
- Manage your own cases, tags, and profile
"""

from .client import (
    ScambusClient,
    build_identifier_type_filter,
    build_combined_filter,
)
from .exceptions import (
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusNotFoundError,
    ScambusValidationError,
)
from .websocket_client import ScambusWebSocketClient
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
    Identifier,
    IdentifierConfidenceUpdate,
    IdentifierLookup,
    ImportDetails,
    JournalEntry,
    Media,
    NoteDetails,
    Notification,
    ObservationDetails,
    Passkey,
    PhoneCallDetails,
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

__version__ = "0.1.0"
__all__ = [
    "ScambusClient",
    "ScambusWebSocketClient",
    "build_identifier_type_filter",
    "build_combined_filter",
    "ScambusAPIError",
    "ScambusAuthenticationError",
    "ScambusValidationError",
    "ScambusNotFoundError",
    "JournalEntry",
    "Identifier",
    "IdentifierLookup",
    "Evidence",
    "Media",
    "PhoneCallDetails",
    "EmailDetails",
    "TextConversationDetails",
    "DetectionDetails",
    "ImportDetails",
    "ExportDetails",
    "ValidationDetails",
    "ContactDetails",
    "ResearchDetails",
    "AnalysisDetails",
    "ActionDetails",
    "ObservationDetails",
    "NoteDetails",
    "UpdateDetails",
    "TagOperationDetails",
    "IdentifierConfidenceUpdate",
    "ConfidenceOperationDetails",
    "ActivityCompleteDetails",
    "Case",
    "CaseComment",
    "ExportStream",
    "Tag",
    "TagValue",
    "Notification",
    "Session",
    "Passkey",
    "View",
]
