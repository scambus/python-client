"""Scambus MCP Server — exposes SCAMBUS fraud detection platform to AI agents."""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from scambus_client import ScambusClient

from .config import get_api_key, get_api_url

logger = logging.getLogger("scambus_mcp")

server = Server("scambus")

_client: ScambusClient | None = None


def _get_client() -> ScambusClient:
    global _client
    if _client is None:
        api_url = get_api_url()
        key_id, key_secret = get_api_key()
        _client = ScambusClient(api_url=api_url, api_key_id=key_id, api_key_secret=key_secret)
    return _client


def _json_response(data: Any) -> list[TextContent]:
    """Serialize data to JSON text content for MCP response."""
    if hasattr(data, "__dict__") and not isinstance(data, dict):
        text = json.dumps(data.__dict__, default=str, indent=2)
    elif isinstance(data, list) and data and hasattr(data[0], "__dict__"):
        text = json.dumps([item.__dict__ if hasattr(item, "__dict__") else item for item in data], default=str, indent=2)
    else:
        text = json.dumps(data, default=str, indent=2)
    return [TextContent(type="text", text=text)]


# ──────────────────────────────────────────────
# Tool definitions
# ──────────────────────────────────────────────

TOOLS = [
    Tool(
        name="search_identifiers",
        description=(
            "Search identifiers (phone numbers, emails, bank accounts, crypto wallets, URLs, etc.) "
            "in the SCAMBUS fraud detection database. Supports filtering by type, tags, confidence "
            "scores, date ranges, geographic details, and more. Returns paginated results with "
            "redacted PII — use enriched_details for analytical metadata (area codes, regions, "
            "institutions, platforms). Use cursor for pagination."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (matches redacted display values and enriched details)"},
                "types": {"type": "array", "items": {"type": "string"}, "description": "Filter by identifier types: phone, email, bank_account, crypto_wallet, social_media, payment_token, url, company"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tag names"},
                "min_confidence": {"type": "number", "description": "Minimum confidence score (0.0-1.0)"},
                "max_confidence": {"type": "number", "description": "Maximum confidence score (0.0-1.0)"},
                "country": {"type": "string", "description": "Filter by country code"},
                "region": {"type": "string", "description": "Filter by geographic region"},
                "area_code": {"type": "string", "description": "Filter by phone area code"},
                "institution": {"type": "string", "description": "Filter by bank institution name"},
                "platform": {"type": "string", "description": "Filter by social media platform"},
                "service": {"type": "string", "description": "Filter by payment service (zelle, cashapp, venmo, etc.)"},
                "domain_category": {"type": "string", "description": "Filter by URL domain category"},
                "is_ours": {"type": "boolean", "description": "Filter to our own identifiers only"},
                "created_after": {"type": "string", "description": "Filter identifiers created after this ISO date"},
                "created_before": {"type": "string", "description": "Filter identifiers created before this ISO date"},
                "limit": {"type": "integer", "description": "Max results (1-500, default 50)", "default": 50},
                "cursor": {"type": "string", "description": "Pagination cursor from previous response"},
            },
        },
    ),
    Tool(
        name="query_journal_entries",
        description=(
            "Query journal entries (scam reports, phone calls, emails, text conversations, "
            "detections, notes, etc.) in the SCAMBUS database. Journal entries describe fraud "
            "activity and are linked to identifiers. Supports filtering by type, date range, "
            "tags, confidence, and free-text search."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "search_query": {"type": "string", "description": "Full-text search in entry descriptions"},
                "entry_type": {"type": "string", "description": "Filter by type: phone_call, email, text_conversation, scam_report, detection, note, import, export, action, analysis, activity_complete"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tag names"},
                "min_confidence": {"type": "number", "description": "Minimum confidence score (0.0-1.0)"},
                "max_confidence": {"type": "number", "description": "Maximum confidence score (0.0-1.0)"},
                "performed_after": {"type": "string", "description": "Filter entries performed after this ISO date"},
                "performed_before": {"type": "string", "description": "Filter entries performed before this ISO date"},
                "include_identifiers": {"type": "boolean", "description": "Include linked identifiers in response (default false)", "default": False},
                "cursor": {"type": "string", "description": "Pagination cursor from previous response"},
            },
        },
    ),
    Tool(
        name="search_cases",
        description=(
            "Search and list investigation cases in SCAMBUS. Cases group related identifiers "
            "and journal entries for organized fraud investigation."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for case titles/descriptions"},
                "status": {"type": "string", "description": "Filter by status: open, in_progress, closed, archived"},
                "limit": {"type": "integer", "description": "Max results (default 50)", "default": 50},
            },
        },
    ),
    Tool(
        name="get_identifier",
        description=(
            "Get detailed information about a specific identifier by its UUID. Returns type, "
            "redacted display value, confidence score, tags, enriched details (area code, region, "
            "country, institution, platform, etc.), network size, and classification."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "identifier_id": {"type": "string", "description": "UUID of the identifier"},
            },
            "required": ["identifier_id"],
        },
    ),
    Tool(
        name="get_journal_entry",
        description=(
            "Get detailed information about a specific journal entry by its UUID. Returns entry "
            "type, description, timestamps, tags, linked identifiers, and metadata."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entry_id": {"type": "string", "description": "UUID of the journal entry"},
            },
            "required": ["entry_id"],
        },
    ),
    Tool(
        name="get_case",
        description=(
            "Get detailed information about a specific investigation case by its UUID. Returns "
            "case title, description, status, priority, linked identifiers, and journal entries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "UUID of the case"},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="get_identifier_network",
        description=(
            "Get the connection network/graph for an identifier. Shows how identifiers are "
            "connected through shared journal entries and cases. Useful for understanding "
            "fraud networks and relationships between phone numbers, emails, bank accounts, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "identifier_id": {"type": "string", "description": "UUID of the identifier to get the network for"},
                "depth": {"type": "integer", "description": "Graph traversal depth (1-5, default 2)", "default": 2},
                "max_nodes": {"type": "integer", "description": "Maximum number of nodes to return (default 50)", "default": 50},
            },
            "required": ["identifier_id"],
        },
    ),
    Tool(
        name="get_identifier_journal_entries",
        description=(
            "Get journal entries linked to a specific identifier. Shows the activity history "
            "for a phone number, email, bank account, etc."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "identifier_id": {"type": "string", "description": "UUID of the identifier"},
                "page": {"type": "integer", "description": "Page number (default 1)", "default": 1},
                "page_size": {"type": "integer", "description": "Results per page (1-100, default 25)", "default": 25},
            },
            "required": ["identifier_id"],
        },
    ),
    Tool(
        name="list_tags",
        description=(
            "List all available tags in SCAMBUS. Tags are used to classify identifiers and "
            "journal entries (e.g., scam type, fraud category, investigation status)."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_filter_options",
        description=(
            "Get available filter values for building queries. Returns distinct values for "
            "entry types, identifier types, originator types, and other filterable fields."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_confidence_history",
        description=(
            "Get the confidence score history for an identifier, showing how confidence "
            "has changed over time based on evidence and reports."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "identifier_id": {"type": "string", "description": "UUID of the identifier"},
            },
            "required": ["identifier_id"],
        },
    ),
    Tool(
        name="get_journal_entry_identifier_summary",
        description=(
            "Get a count of distinct identifiers attached to a journal entry and all of "
            "its descendants, grouped by identifier type. For payment_token and "
            "social_media types, the result also includes a per-subtype breakdown "
            "(e.g. zelle/venmo/cashapp for payment_token, instagram/tiktok for "
            "social_media). Counts are deduplicated — an identifier linked to multiple "
            "descendants only contributes once. Use this to quickly understand what "
            "kinds of identifiers an ingested conversation or case contains without "
            "fetching every identifier individually."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "entry_id": {
                    "type": "string",
                    "description": "UUID of the journal entry",
                },
                "type": {
                    "type": "string",
                    "description": (
                        "Optional identifier type to filter by (phone, email, url, "
                        "payment_token, social_media, bank_account, crypto_wallet, "
                        "company, ...)"
                    ),
                },
            },
            "required": ["entry_id"],
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    client = _get_client()

    try:
        if name == "search_identifiers":
            return _handle_search_identifiers(client, arguments)
        elif name == "query_journal_entries":
            return _handle_query_journal_entries(client, arguments)
        elif name == "search_cases":
            return _handle_search_cases(client, arguments)
        elif name == "get_identifier":
            return _handle_get_identifier(client, arguments)
        elif name == "get_journal_entry":
            return _handle_get_journal_entry(client, arguments)
        elif name == "get_case":
            return _handle_get_case(client, arguments)
        elif name == "get_identifier_network":
            return _handle_get_identifier_network(client, arguments)
        elif name == "get_identifier_journal_entries":
            return _handle_get_identifier_journal_entries(client, arguments)
        elif name == "list_tags":
            return _handle_list_tags(client)
        elif name == "get_filter_options":
            return _handle_get_filter_options(client)
        elif name == "get_confidence_history":
            return _handle_get_confidence_history(client, arguments)
        elif name == "get_journal_entry_identifier_summary":
            return _handle_get_journal_entry_identifier_summary(client, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.exception("Tool %s failed", name)
        return [TextContent(type="text", text=f"Error: {e}")]


# ──────────────────────────────────────────────
# Tool implementations
# ──────────────────────────────────────────────


def _build_filter_criteria(args: dict[str, Any]) -> dict[str, Any] | None:
    """Build a filter_criteria dict from common filter arguments."""
    fc = {}
    if args.get("tags"):
        fc["tag_names"] = args["tags"]
    if args.get("min_confidence") is not None:
        fc["min_confidence"] = args["min_confidence"]
    if args.get("max_confidence") is not None:
        fc["max_confidence"] = args["max_confidence"]
    if args.get("country"):
        fc["country"] = args["country"]
    if args.get("region"):
        fc["region"] = args["region"]
    if args.get("area_code"):
        fc["area_code"] = args["area_code"]
    if args.get("institution"):
        fc["institution"] = args["institution"]
    if args.get("platform"):
        fc["platform"] = args["platform"]
    if args.get("service"):
        fc["service"] = args["service"]
    if args.get("domain_category"):
        fc["domain_category"] = args["domain_category"]
    if args.get("is_ours") is not None:
        fc["is_ours"] = args["is_ours"]
    if args.get("created_after"):
        fc["created_after"] = args["created_after"]
    if args.get("created_before"):
        fc["created_before"] = args["created_before"]
    if args.get("performed_after"):
        fc["performed_after"] = args["performed_after"]
    if args.get("performed_before"):
        fc["performed_before"] = args["performed_before"]
    return fc if fc else None


def _handle_search_identifiers(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    fc = _build_filter_criteria(args)
    result = client.search_identifiers(
        query=args.get("query"),
        types=args.get("types"),
        limit=args.get("limit", 50),
        cursor=args.get("cursor"),
        filter_criteria=fc,
    )
    # Serialize identifier objects in data
    data = []
    for item in result.get("data", []):
        if hasattr(item, "__dict__"):
            data.append(item.__dict__)
        else:
            data.append(item)
    output = {
        "data": data,
        "nextCursor": result.get("nextCursor"),
        "hasMore": result.get("hasMore", False),
        "estimatedTotal": result.get("estimatedTotal"),
        "count": len(data),
    }
    return [TextContent(type="text", text=json.dumps(output, default=str, indent=2))]


def _handle_query_journal_entries(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    fc = _build_filter_criteria(args)
    result = client.query_journal_entries(
        search_query=args.get("search_query"),
        entry_type=args.get("entry_type"),
        include_identifiers=args.get("include_identifiers", False),
        cursor=args.get("cursor"),
        filter_criteria=fc,
    )
    data = []
    for item in result.get("data", []):
        if hasattr(item, "__dict__"):
            data.append(item.__dict__)
        else:
            data.append(item)
    output = {
        "data": data,
        "nextCursor": result.get("nextCursor"),
        "hasMore": result.get("hasMore", False),
        "estimatedTotal": result.get("estimatedTotal"),
        "count": len(data),
    }
    return [TextContent(type="text", text=json.dumps(output, default=str, indent=2))]


def _handle_search_cases(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    result = client.search_cases(
        query=args.get("query"),
        status=args.get("status"),
        limit=args.get("limit", 50),
    )
    return _json_response(result)


def _handle_get_identifier(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    result = client.get_identifier(args["identifier_id"])
    return _json_response(result)


def _handle_get_journal_entry(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    result = client.get_journal_entry(args["entry_id"])
    return _json_response(result)


def _handle_get_case(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    result = client.get_case(args["case_id"])
    return _json_response(result)


def _handle_get_identifier_network(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    identifier_id = args["identifier_id"]
    depth = args.get("depth", 2)
    max_nodes = args.get("max_nodes", 50)
    # Use the client's session to call the graph endpoint directly
    response = client.session.get(
        f"{client.api_url}/identifiers/{identifier_id}/graph",
        params={"depth": depth, "max_nodes": max_nodes},
    )
    response.raise_for_status()
    return [TextContent(type="text", text=json.dumps(response.json(), default=str, indent=2))]


def _handle_get_identifier_journal_entries(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    identifier_id = args["identifier_id"]
    page = args.get("page", 1)
    page_size = args.get("page_size", 25)
    response = client.session.get(
        f"{client.api_url}/identifiers/{identifier_id}/journal-entries",
        params={"page": page, "page_size": page_size},
    )
    response.raise_for_status()
    return [TextContent(type="text", text=json.dumps(response.json(), default=str, indent=2))]


def _handle_list_tags(client: ScambusClient) -> list[TextContent]:
    result = client.list_tags()
    return _json_response(result)


def _handle_get_filter_options(client: ScambusClient) -> list[TextContent]:
    response = client.session.get(f"{client.api_url}/filter-options")
    response.raise_for_status()
    return [TextContent(type="text", text=json.dumps(response.json(), default=str, indent=2))]


def _handle_get_confidence_history(client: ScambusClient, args: dict[str, Any]) -> list[TextContent]:
    identifier_id = args["identifier_id"]
    response = client.session.get(f"{client.api_url}/confidence/identifiers/{identifier_id}")
    response.raise_for_status()
    return [TextContent(type="text", text=json.dumps(response.json(), default=str, indent=2))]


def _handle_get_journal_entry_identifier_summary(
    client: ScambusClient, args: dict[str, Any]
) -> list[TextContent]:
    summary = client.get_identifier_summary(
        args["entry_id"],
        identifier_type=args.get("type"),
    )
    payload = {
        "journal_entry_id": summary.journal_entry_id,
        "total": summary.total,
        "by_type": [
            {
                "type": tc.type,
                "count": tc.count,
                "by_subtype": [
                    {"subtype": sc.subtype, "count": sc.count}
                    for sc in tc.by_subtype
                ],
            }
            for tc in summary.by_type
        ],
    }
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────


def main():
    import asyncio

    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())
