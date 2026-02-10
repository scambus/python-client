"""Input types for the Scambus SDK.

These types provide a typed interface for SDK operations, similar to AWS CDK.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union


class IdentifierType:
    """Identifier type constants."""

    PHONE = "phone"
    EMAIL = "email"
    URL = "url"
    BANK_ACCOUNT = "bank_account"
    CRYPTO_WALLET = "crypto_wallet"
    SOCIAL_MEDIA = "social_media"
    ZELLE = "zelle"
    PAYMENT_TOKEN = "payment_token"


class JournalEntryType:
    """Journal entry type constants."""

    PHONE_CALL = "phone_call"
    EMAIL = "email"
    TEXT_CONVERSATION = "text_conversation"
    CONVERSATION_CONTINUATION = "conversation_continuation"
    WEB_INTERACTION = "web_interaction"
    DETECTION = "detection"
    IMPORT = "import"
    EXPORT = "export"
    VALIDATION = "validation"
    NOTE = "note"
    TAG_OPERATION = "tag_operation"
    CONFIDENCE_OPERATION = "confidence_operation"
    REDACTION = "redaction"
    CASE_UPDATE = "case_update"
    CASE_IDENTIFIER_LINK = "case_identifier_link"
    CASE_IDENTIFIER_UNLINK = "case_identifier_unlink"
    KARMA_ADJUSTMENT = "karma_adjustment"
    ACTIVITY_COMPLETE = "activity_complete"
    DATA = "data"
    TASK_UPDATE = "task_update"
    TASK_ASSIGNMENT = "task_assignment"
    CASE_HANDOFF = "case_handoff"


class StreamDataType:
    """Export stream data type constants."""

    JOURNAL_ENTRY = "journal_entry"
    IDENTIFIER = "identifier"


@dataclass
class TagLookup:
    """Tag lookup for applying tags to journal entries.

    Examples:
        # Boolean tag
        TagLookup(tag_name="HighPriority")

        # Valued tag
        TagLookup(tag_name="ScamType", tag_value="Phishing")
    """

    tag_name: str
    tag_value: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API."""
        result = {"tag_name": self.tag_name}
        if self.tag_value is not None:
            result["tag_value"] = self.tag_value
        return result


@dataclass
class FilterCriteria:
    """Unified filter criteria used across search, query, views, and export streams.

    All fields are optional. Only non-None fields are included in the API request.
    Field names use snake_case matching the backend Go struct.

    Examples:
        # Simple type + confidence filter
        FilterCriteria(types=["phone", "email"], min_confidence=0.8)

        # Date range with text search
        FilterCriteria(
            search_query="phishing",
            created_after="2025-01-01T00:00:00Z",
            created_before="2025-07-01T00:00:00Z",
        )

        # Exclusion filters
        FilterCriteria(
            status=["open"],
            excluded_types=["note"],
            exclude_human_reviewed=True,
        )

        # Identifier enriched details
        FilterCriteria(
            type="phone",
            toll_free=True,
            country="US",
        )
    """

    # Text search
    search_query: Optional[str] = None
    negate_search_query: Optional[bool] = None

    # Core arrays
    status: Optional[List[str]] = None
    priority: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    types: Optional[List[str]] = None
    originator_ids: Optional[List[str]] = None
    proxy_originator_ids: Optional[List[str]] = None
    originator_types: Optional[List[str]] = None
    org_ids: Optional[List[str]] = None

    # Single type
    type: Optional[str] = None
    identifier_type: Optional[str] = None

    # Confidence
    confidence_range: Optional[str] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None

    # Dates (ISO-8601 strings)
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    performed_after: Optional[str] = None
    performed_before: Optional[str] = None
    discovered_after: Optional[str] = None
    discovered_before: Optional[str] = None
    confidence_changed_after: Optional[str] = None
    confidence_changed_before: Optional[str] = None

    # Originator config
    originator_filter_type: Optional[str] = None  # "originator", "proxy_originator", or "both"

    # JSONB
    details: Optional[Dict[str, Any]] = None
    excluded_details: Optional[Dict[str, Any]] = None

    # Booleans
    has_media: Optional[bool] = None
    has_notes: Optional[bool] = None
    is_ours: Optional[bool] = None
    human_reviewed: Optional[bool] = None
    exclude_human_reviewed: Optional[bool] = None
    user_pinned: Optional[bool] = None
    is_test: Optional[bool] = None
    include_identifiers: Optional[bool] = None
    include_evidence: Optional[bool] = None

    # Identifier enriched details
    toll_free: Optional[bool] = None
    institution: Optional[str] = None
    platform: Optional[str] = None
    service: Optional[str] = None
    area_code: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    domain_category: Optional[str] = None
    is_private_suffix: Optional[bool] = None
    routing_number_owner: Optional[str] = None

    # Assignment
    assigned_to: Optional[str] = None

    # Tag names
    tag_names: Optional[List[str]] = None
    excluded_tag_names: Optional[List[str]] = None

    # Exclusion arrays
    excluded_status: Optional[List[str]] = None
    excluded_priority: Optional[List[str]] = None
    excluded_tags: Optional[List[str]] = None
    excluded_types: Optional[List[str]] = None
    excluded_originator_types: Optional[List[str]] = None
    excluded_originator_ids: Optional[List[str]] = None
    excluded_proxy_originator_ids: Optional[List[str]] = None
    excluded_org_ids: Optional[List[str]] = None

    # Exclusion config
    excluded_originator_filter_type: Optional[str] = None

    # Negation flags
    negate_has_media: Optional[bool] = None
    negate_is_ours: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API, only including non-None fields."""
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                result[k] = v
        return result


@dataclass
class StreamFilter:
    """Filter configuration for export streams.

    .. deprecated::
        Use :class:`FilterCriteria` instead. StreamFilter is kept for backward
        compatibility but FilterCriteria provides the full set of filter fields.

    Examples:
        StreamFilter(
            identifier_types=["phone", "email"],
            min_confidence=0.8,
            max_confidence=1.0
        )
    """

    identifier_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    include_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API."""
        result = {}
        if self.identifier_types:
            # Go FilterCriteria has identifier_type as a singular *string,
            # not a list. Use the first value.
            result["identifier_type"] = self.identifier_types[0]
        if self.min_confidence is not None:
            result["min_confidence"] = self.min_confidence
        if self.max_confidence is not None:
            result["max_confidence"] = self.max_confidence
        if self.include_tags is not None:
            result["include_tags"] = self.include_tags
        if self.exclude_tags is not None:
            result["exclude_tags"] = self.exclude_tags
        return result


@dataclass
class ViewFilter:
    """Filter criteria for saved views.

    .. deprecated::
        Use :class:`FilterCriteria` instead. ViewFilter is kept for backward
        compatibility but FilterCriteria provides the full set of filter fields.

    Examples:
        ViewFilter(
            identifier_types=["phone"],
            min_confidence=0.9,
            entry_types=["detection", "phone_call"]
        )
    """

    identifier_types: Optional[List[str]] = None
    entry_types: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    max_confidence: Optional[float] = None
    performed_after: Optional[str] = None
    performed_before: Optional[str] = None
    search_query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API."""
        result = {}
        if self.identifier_types:
            # Go FilterCriteria has identifier_type as a singular *string
            result["identifier_type"] = self.identifier_types[0]
        if self.entry_types is not None:
            result["types"] = self.entry_types
        if self.min_confidence is not None:
            result["min_confidence"] = self.min_confidence
        if self.max_confidence is not None:
            result["max_confidence"] = self.max_confidence
        if self.performed_after is not None:
            result["performed_after"] = self.performed_after
        if self.performed_before is not None:
            result["performed_before"] = self.performed_before
        if self.search_query is not None:
            result["search_query"] = self.search_query
        return result


@dataclass
class ViewSortOrder:
    """Sort order configuration for views.

    Examples:
        ViewSortOrder(field="created_at", direction="desc")
    """

    field: str
    direction: str = "desc"  # "asc" or "desc"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API."""
        return {"field": self.field, "direction": self.direction}


# Type aliases for flexibility
TagLookupInput = Union[TagLookup, Dict[str, Any]]
FilterCriteriaInput = Union[FilterCriteria, Dict[str, Any]]
StreamFilterInput = Union[StreamFilter, Dict[str, Any]]
ViewFilterInput = Union[ViewFilter, FilterCriteria, Dict[str, Any]]
ViewSortOrderInput = Union[ViewSortOrder, Dict[str, Any]]


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert an object to dictionary, handling both typed objects and dicts.

    This allows the SDK to accept both typed objects and raw dictionaries for
    backward compatibility and flexibility.
    """
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if v is not None}
    else:
        return obj


def to_dict_list(items: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
    """Convert a list of objects to dictionaries."""
    if items is None:
        return None
    return [to_dict(item) for item in items]
