"""Identifier commands."""

import sys

import click

from scambus_cli.utils import print_detail, print_error, print_info, print_json, print_table


def _identifier_dict(identifier):
    return {
        "id": identifier.id,
        "type": identifier.type,
        "display_value": identifier.display_value,
        "confidence": identifier.confidence,
        "created_at": identifier.created_at.isoformat() if identifier.created_at else None,
        "data": identifier.data,
    }


@click.group()
def identifiers():
    """Browse identifiers."""
    pass


@identifiers.command("list")
@click.option("--type", "identifier_type", help="Filter by type (phone, email, ...)")
@click.option("--page", default=1, show_default=True, help="Page number")
@click.option("--limit", default=20, show_default=True, help="Items per page (max 100)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_identifiers(ctx, identifier_type, page, limit, output_json):
    """List identifiers, newest first.

    Examples:
        scambus identifiers list
        scambus identifiers list --type phone --limit 50
    """
    client = ctx.obj.get_client()

    try:
        identifier_list = client.list_identifiers(
            identifier_type=identifier_type, page=page, limit=limit
        )

        if output_json:
            print_json([_identifier_dict(i) for i in identifier_list])
        elif not identifier_list:
            print_info("No identifiers found")
        else:
            table_data = [
                {
                    "ID": i.id,
                    "Type": i.type,
                    "Value": i.display_value[:50],
                    "Created": i.created_at.strftime("%Y-%m-%d") if i.created_at else "N/A",
                }
                for i in identifier_list
            ]
            print_table(table_data, title=f"Identifiers (page {page})")

    except Exception as e:
        print_error(f"Failed to list identifiers: {e}")
        sys.exit(1)


@identifiers.command()
@click.argument("identifier_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, identifier_id, output_json):
    """Get identifier details.

    Examples:
        scambus identifiers get <identifier-id>
    """
    client = ctx.obj.get_client()

    try:
        identifier = client.get_identifier(identifier_id)

        if output_json:
            print_json(_identifier_dict(identifier))
        else:
            print_detail(_identifier_dict(identifier), title=identifier.display_value)

    except Exception as e:
        print_error(f"Failed to get identifier: {e}")
        sys.exit(1)
