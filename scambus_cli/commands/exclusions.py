"""Identifier exclusion management commands."""

import sys

import click

from scambus_cli.utils import (
    print_error,
    print_info,
    print_json,
    print_success,
    print_table,
)


@click.group()
def exclusions():
    """Manage identifier exclusions."""
    pass


@exclusions.command("list")
@click.option("--page", default=1, help="Page number")
@click.option("--limit", default=25, help="Items per page")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_exclusions(ctx, page, limit, output_json):
    """List identifier exclusions for your organization.

    Examples:
        scambus exclusions list
        scambus exclusions list --json
    """
    client = ctx.obj.get_client()

    try:
        items = client.list_identifier_exclusions(page=page, limit=limit)

        if not items:
            print_info("No exclusions found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": e.id,
                        "identifier_type": e.identifier_type,
                        "display_value": e.display_value,
                        "reason": e.reason,
                        "created_at": e.created_at,
                    }
                    for e in items
                ]
            )
        else:
            table_data = [
                {
                    "ID": e.id[:8],
                    "Type": e.identifier_type,
                    "Value": e.display_value,
                    "Reason": e.reason or "",
                }
                for e in items
            ]
            print_table(table_data, title=f"Identifier Exclusions ({len(items)})")

    except Exception as e:
        print_error(f"Failed to list exclusions: {e}")
        sys.exit(1)


@exclusions.command()
@click.option("--identifier-id", help="UUID of an existing identifier to exclude")
@click.option("--type", "identifier_type", help="Identifier type (email, phone, url, etc.)")
@click.option("--value", help="Identifier value to exclude")
@click.option("--reason", help="Reason for exclusion")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(ctx, identifier_id, identifier_type, value, reason, output_json):
    """Create an identifier exclusion.

    Provide either --identifier-id (to exclude an existing identifier) or both
    --type and --value (to exclude by type+value).

    Examples:
        scambus exclusions create --identifier-id 001ce030-2687-46cd-ac39-84582d9f97c0
        scambus exclusions create --type email --value scammer@evil.com --reason "Known false positive"
        scambus exclusions create --type phone --value "+15551234567"
    """
    client = ctx.obj.get_client()

    if not identifier_id and not (identifier_type and value):
        print_error("Provide either --identifier-id or both --type and --value")
        sys.exit(1)

    try:
        exclusion = client.create_identifier_exclusion(
            identifier_id=identifier_id,
            identifier_type=identifier_type,
            value=value,
            reason=reason,
        )

        if output_json:
            print_json(
                {
                    "id": exclusion.id,
                    "identifier_type": exclusion.identifier_type,
                    "display_value": exclusion.display_value,
                    "reason": exclusion.reason,
                    "created_at": exclusion.created_at,
                }
            )
        else:
            print_success(
                f"Excluded {exclusion.identifier_type}: {exclusion.display_value}"
            )

    except Exception as e:
        print_error(f"Failed to create exclusion: {e}")
        sys.exit(1)


@exclusions.command()
@click.argument("exclusion_id")
@click.pass_context
def delete(ctx, exclusion_id):
    """Delete an identifier exclusion.

    Examples:
        scambus exclusions delete 001ce030-2687-46cd-ac39-84582d9f97c0
    """
    client = ctx.obj.get_client()

    try:
        client.delete_identifier_exclusion(exclusion_id)
        print_success("Exclusion deleted")
    except Exception as e:
        print_error(f"Failed to delete exclusion: {e}")
        sys.exit(1)
