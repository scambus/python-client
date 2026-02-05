"""File export commands."""

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
def exports():
    """Manage file exports (CSV, JSON, etc.)."""
    pass


@exports.command("create")
@click.option(
    "--source-type",
    required=True,
    type=click.Choice(["view", "search"], case_sensitive=False),
    help="Source type for the export",
)
@click.option("--source-id", help="View ID when source-type is 'view'")
@click.option(
    "--entity-type",
    required=True,
    type=click.Choice(["journal", "cases", "identifiers", "evidence"], case_sensitive=False),
    help="Entity type to export",
)
@click.option(
    "--format",
    "export_format",
    default="csv",
    help="Export format (default: csv)",
)
@click.option("--name", help="Export name (auto-generated if not provided)")
@click.option(
    "--column",
    "columns",
    multiple=True,
    help="Column to include (can specify multiple)",
)
@click.option("--limit", type=int, help="Maximum number of rows")
@click.option("--date-range-start", help="Start of date range (ISO format)")
@click.option("--date-range-end", help="End of date range (ISO format)")
@click.option("--include-ours", is_flag=True, help="Include items from your org")
@click.option("--filter-json", help="FilterCriteria as JSON string")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create_export(
    ctx, source_type, source_id, entity_type, export_format, name, columns,
    limit, date_range_start, date_range_end, include_ours, filter_json, output_json,
):
    """Create a new file export.

    Examples:
        scambus exports create --source-type view --source-id VIEW_ID --entity-type journal --format csv
        scambus exports create --source-type search --entity-type identifiers --filter-json '{"types": ["phone"]}'
    """
    client = ctx.obj.get_client()

    try:
        fc = None
        if filter_json:
            try:
                fc = json.loads(filter_json)
            except json.JSONDecodeError:
                print_error("Invalid JSON in --filter-json")
                sys.exit(1)

        result = client.create_file_export(
            source_type=source_type,
            source_id=source_id,
            entity_type=entity_type,
            format=export_format,
            name=name,
            columns=list(columns) if columns else None,
            limit=limit,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            include_ours=include_ours,
            filter_criteria=fc,
        )

        if output_json:
            print_json(result)
        else:
            print_success(f"File export created: {result.get('id', 'unknown')}")
            print_detail(
                {
                    "ID": result.get("id", "N/A"),
                    "Status": result.get("status", "N/A"),
                    "Format": result.get("format", "N/A"),
                    "Entity Type": result.get("entity_type", "N/A"),
                },
                title="Created Export",
            )

    except Exception as e:
        print_error(f"Failed to create export: {e}")
        sys.exit(1)


@exports.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_exports(ctx, output_json):
    """List file exports.

    Examples:
        scambus exports list
        scambus exports list --json
    """
    client = ctx.obj.get_client()

    try:
        results = client.list_file_exports()

        if not results:
            print_info("No file exports found")
            return

        if output_json:
            print_json(results)
        else:
            table_data = [
                {
                    "ID": r.get("id", "")[:8],
                    "Name": r.get("name", "N/A"),
                    "Status": r.get("status", "N/A"),
                    "Format": r.get("format", "N/A"),
                    "Entity": r.get("entity_type", "N/A"),
                }
                for r in results
            ]
            print_table(table_data, title=f"File Exports ({len(results)})")

    except Exception as e:
        print_error(f"Failed to list exports: {e}")
        sys.exit(1)


@exports.command("get")
@click.argument("export_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get_export(ctx, export_id, output_json):
    """Get file export details.

    Examples:
        scambus exports get EXPORT_ID
    """
    client = ctx.obj.get_client()

    try:
        result = client.get_file_export(export_id)

        if output_json:
            print_json(result)
        else:
            print_detail(
                {
                    "ID": result.get("id", "N/A"),
                    "Name": result.get("name", "N/A"),
                    "Status": result.get("status", "N/A"),
                    "Format": result.get("format", "N/A"),
                    "Entity Type": result.get("entity_type", "N/A"),
                    "Row Count": result.get("row_count", "N/A"),
                    "File Size": result.get("file_size", "N/A"),
                },
                title="File Export Details",
            )

    except Exception as e:
        print_error(f"Failed to get export: {e}")
        sys.exit(1)


@exports.command("download")
@click.argument("export_id")
@click.option("-o", "--output", "output_path", required=True, help="Output file path")
@click.pass_context
def download_export(ctx, export_id, output_path):
    """Download a completed file export.

    Examples:
        scambus exports download EXPORT_ID -o output.csv
    """
    client = ctx.obj.get_client()

    try:
        client.download_file_export(export_id, output_path)
        print_success(f"Downloaded to: {output_path}")

    except Exception as e:
        print_error(f"Failed to download export: {e}")
        sys.exit(1)


@exports.command("delete")
@click.argument("export_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_export(ctx, export_id, yes):
    """Delete a file export.

    Examples:
        scambus exports delete EXPORT_ID
        scambus exports delete EXPORT_ID --yes
    """
    client = ctx.obj.get_client()

    if not yes:
        click.confirm(f"Are you sure you want to delete export {export_id}?", abort=True)

    try:
        client.delete_file_export(export_id)
        print_success(f"Export deleted: {export_id}")

    except Exception as e:
        print_error(f"Failed to delete export: {e}")
        sys.exit(1)
