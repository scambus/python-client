"""Input types for the Scambus SDK.

These types provide a typed interface for SDK operations, similar to AWS CDK.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union


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
class StreamFilter:
    """Filter configuration for export streams.

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
        if self.identifier_types is not None:
            result["identifier_types"] = self.identifier_types
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
        if self.identifier_types is not None:
            result["identifier_types"] = self.identifier_types
        if self.entry_types is not None:
            result["entry_types"] = self.entry_types
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
StreamFilterInput = Union[StreamFilter, Dict[str, Any]]
ViewFilterInput = Union[ViewFilter, Dict[str, Any]]
ViewSortOrderInput = Union[ViewSortOrder, Dict[str, Any]]


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert an object to dictionary, handling both typed objects and dicts.

    This allows the SDK to accept both typed objects and raw dictionaries for
    backward compatibility and flexibility.
    """
    if isinstance(obj, dict):
        return obj
    elif hasattr(obj, 'to_dict'):
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):
        return {k: v for k, v in obj.__dict__.items() if v is not None}
    else:
        return obj


def to_dict_list(items: Optional[List[Any]]) -> Optional[List[Dict[str, Any]]]:
    """Convert a list of objects to dictionaries."""
    if items is None:
        return None
    return [to_dict(item) for item in items]
