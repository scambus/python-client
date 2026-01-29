"""View management commands."""

import json
import sys

import click

from scambus_cli.utils import (
    print_detail,
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
)


@click.group()
def views():
    """Manage views (saved queries)."""
    pass


@views.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_views(ctx, output_json):
    """List all available views.

    Examples:
        scambus views list
        scambus views list --json
    """
    client = ctx.obj.get_client()

    try:
        view_list = client.list_views()

        if not view_list:
            print_info("No views found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": v.id,
                        "name": v.name,
                        "description": v.description,
                        "alias": v.alias,
                        "entity_type": v.entity_type,
                        "visibility": v.visibility,
                        "is_system": v.is_system,
                        "created_at": (v.created_at.isoformat() if v.created_at else None),
                    }
                    for v in view_list
                ]
            )
        else:
            table_data = [
                {
                    "ID": v.id[:8],
                    "Name": v.name,
                    "Alias": v.alias or "N/A",
                    "Type": v.entity_type,
                    "Visibility": v.visibility,
                    "System": "Yes" if v.is_system else "No",
                }
                for v in view_list
            ]

            print_table(table_data, title=f"Views ({len(view_list)})")

    except Exception as e:
        print_error(f"Failed to list views: {e}")
        sys.exit(1)


@views.command("get")
@click.argument("view_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get_view(ctx, view_id, output_json):
    """Get details of a specific view.

    VIEW_ID can be a UUID or an alias (e.g., "my-journal-entries")

    Examples:
        scambus views get my-journal-entries
        scambus views get 123e4567-e89b-12d3-a456-426614174000
    """
    client = ctx.obj.get_client()

    try:
        view = client.get_view(view_id)

        if output_json:
            print_json(
                {
                    "id": view.id,
                    "name": view.name,
                    "description": view.description,
                    "alias": view.alias,
                    "entity_type": view.entity_type,
                    "visibility": view.visibility,
                    "view_type": view.view_type,
                    "is_system": view.is_system,
                    "filter_criteria": view.filter_criteria,
                    "sort_order": view.sort_order,
                    "created_at": view.created_at.isoformat() if view.created_at else None,
                    "updated_at": view.updated_at.isoformat() if view.updated_at else None,
                }
            )
        else:
            details = {
                "ID": view.id,
                "Name": view.name,
                "Alias": view.alias or "N/A",
                "Entity Type": view.entity_type,
                "Visibility": view.visibility,
                "View Type": view.view_type,
                "System View": "Yes" if view.is_system else "No",
            }
            if view.description:
                details["Description"] = view.description

            print_detail(details, title="View Details")

            if view.filter_criteria:
                print_info("\nFilter Criteria:")
                print(json.dumps(view.filter_criteria, indent=2))

            if view.sort_order:
                print_info("\nSort Order:")
                print(json.dumps(view.sort_order, indent=2))

    except Exception as e:
        print_error(f"Failed to get view: {e}")
        sys.exit(1)


@views.command("execute")
@click.argument("view_id")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option("--cursor", help="Pagination cursor")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow mode: show results then stream new matches (journal views only)",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def execute_view(ctx, view_id, limit, cursor, follow, output_json):
    """Execute a saved view query.

    VIEW_ID can be a UUID or an alias (e.g., "my-journal-entries")

    Use --follow (-f) to watch for new matching entries in real-time (journal views only).

    Examples:
        scambus views execute my-journal-entries
        scambus views execute my-journal-entries --limit 10
        scambus views execute my-journal-entries --follow
        scambus views execute 123e4567-e89b-12d3-a456-426614174000 --json
    """
    client = ctx.obj.get_client()

    try:
        result = client.execute_view(view_id, cursor=cursor, limit=limit)

        data = result.get("data", [])
        has_more = result.get("hasMore", False)
        next_cursor = result.get("nextCursor")
        count = result.get("count", 0)
        entity_type = result.get("entity_type", "unknown")

        if not data:
            print_info("No results found")
            return

        if output_json:
            print_json(
                {
                    "data": data,
                    "count": count,
                    "hasMore": has_more,
                    "nextCursor": next_cursor,
                    "entity_type": entity_type,
                }
            )
        else:
            # Display results based on entity type
            if entity_type == "journal":
                table_data = [
                    {
                        "ID": item.get("id", "")[:8] if isinstance(item, dict) else str(item)[:8],
                        "Type": item.get("type", "N/A") if isinstance(item, dict) else "N/A",
                        "Created": (
                            item.get("created_at", "N/A")[:19] if isinstance(item, dict) else "N/A"
                        ),
                    }
                    for item in data[:20]  # Limit display to 20 items
                ]
                print_table(
                    table_data, title=f"View Results - {entity_type.title()} ({count} total)"
                )
            else:
                # Generic display for other entity types
                print_info(f"Found {count} {entity_type} entries")
                for i, item in enumerate(data[:10], 1):
                    if isinstance(item, dict):
                        print(f"{i}. {item.get('id', 'unknown')[:16]} - {item.get('name', 'N/A')}")
                    else:
                        print(f"{i}. {str(item)[:60]}")

            if has_more:
                print_info(f"\nMore results available. Use --cursor {next_cursor}")

        # Follow mode: create stream from view and subscribe via WebSocket
        if follow:
            if entity_type != "journal":
                print_error("Follow mode is only supported for journal entity views")
                sys.exit(1)

            import asyncio
            from scambus_client.websocket_client import ScambusWebSocketClient
            from scambus_cli.config import get_api_url
            import time

            print_info("\n==> Entering follow mode (press Ctrl+C to exit)")
            print_info("Creating stream from view...")

            try:
                # Get view details to extract filters
                view = client.get_view(view_id)

                # Create stream from view filters (mark as temporary for auto-cleanup)
                stream_name = f"View Follow: {view.name} ({int(time.time())})"
                stream = client.create_stream(
                    name=stream_name,
                    data_type="journal_entry",
                    filters=view.filters,
                    is_temporary=True,
                )

                print_success(f"Stream created: {stream.id}")
                print_info("Waiting for new matching entries...\n")

                # Create WebSocket client
                api_url = get_api_url()
                ws_client = ScambusWebSocketClient(api_url=api_url)

                new_count = 0

                # Define message handler for follow mode
                def handle_new_entry(entry_data):
                    nonlocal new_count
                    new_count += 1

                    if output_json:
                        # Output as single JSON object per line
                        print_json(entry_data)
                    else:
                        # Pretty print new entry
                        print_info(f"\n==> New Entry #{new_count}")
                        entry_summary = {
                            "ID": entry_data.get("id", "")[:8],
                            "Type": entry_data.get("type", "N/A"),
                            "Description": entry_data.get("description", "")[:80],
                            "Performed": (
                                entry_data.get("performed_at", "N/A")[:19]
                                if entry_data.get("performed_at")
                                else "N/A"
                            ),
                        }
                        print_detail(entry_summary)

                # Run WebSocket listener
                asyncio.run(
                    ws_client.listen_stream(
                        stream_id=stream.id,
                        on_message=handle_new_entry,
                        cursor="$",  # Only new messages
                    )
                )

            except KeyboardInterrupt:
                print_info(f"\n\nFollow mode stopped. Received {new_count} new entries.")
                print_info("Cleaning up temporary stream...")
                try:
                    client.delete_stream(stream.id)
                    print_success("Temporary stream deleted")
                except Exception as cleanup_error:
                    print_error(f"Failed to delete stream {stream.id}: {cleanup_error}")
            except Exception as follow_error:
                print_error(f"Follow mode failed: {follow_error}")
                import traceback

                traceback.print_exc()
                # Try to clean up stream on error
                try:
                    print_info("Cleaning up temporary stream...")
                    client.delete_stream(stream.id)
                    print_success("Temporary stream deleted")
                except:
                    pass  # Ignore cleanup errors on failure

    except Exception as e:
        print_error(f"Failed to execute view: {e}")
        sys.exit(1)


@views.command("create")
@click.option("--name", required=True, help="View name")
@click.option(
    "--entity-type",
    required=True,
    type=click.Choice(["journal", "cases", "identifiers", "evidence"]),
    help="Entity type to query",
)
@click.option("--description", help="View description")
@click.option("--alias", help="Short alias for the view")
@click.option(
    "--visibility",
    type=click.Choice(["private", "organization", "public"]),
    default="organization",
    help="View visibility (default: organization)",
)
@click.option("--filter-criteria", help="Filter criteria as JSON string")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create_view(
    ctx, name, entity_type, description, alias, visibility, filter_criteria, output_json
):
    """Create a new view (saved query).

    Examples:
        scambus views create --name "My Calls" --entity-type journal
        scambus views create --name "High Confidence" --entity-type journal --filter-criteria '{"min_confidence": 0.8}'
    """
    client = ctx.obj.get_client()

    try:
        # Parse filter criteria if provided
        criteria = None
        if filter_criteria:
            try:
                criteria = json.loads(filter_criteria)
            except json.JSONDecodeError:
                print_error("Invalid JSON in filter-criteria")
                sys.exit(1)

        view = client.create_view(
            name=name,
            entity_type=entity_type,
            description=description,
            alias=alias,
            visibility=visibility,
            filter_criteria=criteria,
        )

        if output_json:
            print_json(
                {
                    "id": view.id,
                    "name": view.name,
                    "alias": view.alias,
                    "entity_type": view.entity_type,
                    "visibility": view.visibility,
                }
            )
        else:
            print_success(f"View created: {view.id}")
            details = {
                "ID": view.id,
                "Name": view.name,
                "Entity Type": view.entity_type,
                "Visibility": view.visibility,
            }
            if view.alias:
                details["Alias"] = view.alias
            print_detail(details, title="Created View")

    except Exception as e:
        print_error(f"Failed to create view: {e}")
        sys.exit(1)


@views.command("update")
@click.argument("view_id")
@click.option("--name", help="New view name")
@click.option("--description", help="New description")
@click.option(
    "--visibility",
    type=click.Choice(["private", "organization", "public"]),
    help="New visibility",
)
@click.option("--filter-criteria", help="New filter criteria as JSON string")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def update_view(ctx, view_id, name, description, visibility, filter_criteria, output_json):
    """Update an existing view.

    Examples:
        scambus views update VIEW_ID --name "Updated Name"
        scambus views update VIEW_ID --visibility public
    """
    client = ctx.obj.get_client()

    try:
        # Parse filter criteria if provided
        criteria = None
        if filter_criteria:
            try:
                criteria = json.loads(filter_criteria)
            except json.JSONDecodeError:
                print_error("Invalid JSON in filter-criteria")
                sys.exit(1)

        view = client.update_view(
            view_id=view_id,
            name=name,
            description=description,
            visibility=visibility,
            filter_criteria=criteria,
        )

        if output_json:
            print_json(
                {
                    "id": view.id,
                    "name": view.name,
                    "description": view.description,
                    "visibility": view.visibility,
                }
            )
        else:
            print_success(f"View updated: {view.id}")
            print_detail(
                {
                    "ID": view.id,
                    "Name": view.name,
                    "Visibility": view.visibility,
                },
                title="Updated View",
            )

    except Exception as e:
        print_error(f"Failed to update view: {e}")
        sys.exit(1)


@views.command("delete")
@click.argument("view_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_view(ctx, view_id, yes):
    """Delete a view.

    Examples:
        scambus views delete VIEW_ID
        scambus views delete VIEW_ID --yes
    """
    client = ctx.obj.get_client()

    if not yes:
        click.confirm(f"Are you sure you want to delete view {view_id}?", abort=True)

    try:
        client.delete_view(view_id)
        print_success(f"View deleted: {view_id}")

    except Exception as e:
        print_error(f"Failed to delete view: {e}")
        sys.exit(1)


@views.command("my-journal")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def my_journal(ctx, limit, output_json):
    """Execute the 'My Journal Entries' system view.

    This is a shortcut for viewing journal entries you created.

    Examples:
        scambus views my-journal
        scambus views my-journal --limit 20
    """
    client = ctx.obj.get_client()

    try:
        result = client.execute_my_journal_entries(limit=limit)

        data = result.get("data", [])
        count = result.get("count", 0)

        if not data:
            print_info("No journal entries found")
            return

        if output_json:
            print_json({"data": data, "count": count})
        else:
            table_data = [
                {
                    "ID": item.get("id", "")[:8] if isinstance(item, dict) else str(item)[:8],
                    "Type": item.get("type", "N/A") if isinstance(item, dict) else "N/A",
                    "Created": (
                        item.get("created_at", "N/A")[:19] if isinstance(item, dict) else "N/A"
                    ),
                }
                for item in data[:20]  # Limit display to 20 items
            ]
            print_table(table_data, title=f"My Journal Entries ({count} total)")

    except Exception as e:
        print_error(f"Failed to get journal entries: {e}")
        sys.exit(1)


@views.command("my-pinboard")
@click.option("--limit", type=int, help="Maximum number of results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def my_pinboard(ctx, limit, output_json):
    """Execute the 'My Pinboard' system view.

    This is a shortcut for viewing pinned items.

    Examples:
        scambus views my-pinboard
        scambus views my-pinboard --limit 20
    """
    client = ctx.obj.get_client()

    try:
        result = client.execute_my_pinboard(limit=limit)

        data = result.get("data", [])
        count = result.get("count", 0)

        if not data:
            print_info("No pinned items found")
            return

        if output_json:
            print_json({"data": data, "count": count})
        else:
            print_info(f"Found {count} pinned items")
            for i, item in enumerate(data[:10], 1):
                if isinstance(item, dict):
                    print(f"{i}. {item.get('id', 'unknown')[:16]} - {item.get('name', 'N/A')}")
                else:
                    print(f"{i}. {str(item)[:60]}")

    except Exception as e:
        print_error(f"Failed to get pinboard: {e}")
        sys.exit(1)
