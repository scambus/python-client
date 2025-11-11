"""Case management commands."""

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
def cases():
    """Manage investigation cases."""
    pass


@cases.command("list")
@click.option("--status", help="Filter by status")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_cases(ctx, status, output_json):
    """List your cases.

    Examples:
        scambus cases list
        scambus cases list --status open
    """
    client = ctx.obj.get_client()

    try:
        case_list = client.list_cases(status=status)

        if not case_list:
            print_info("No cases found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": c.id,
                        "title": c.title,
                        "status": c.status,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in case_list
                ]
            )
        else:
            table_data = [
                {
                    "ID": c.id[:8],
                    "Title": c.title,
                    "Status": c.status or "N/A",
                    "Created": c.created_at.strftime("%Y-%m-%d") if c.created_at else "N/A",
                }
                for c in case_list
            ]

            print_table(table_data, title=f"Cases ({len(case_list)})")

    except Exception as e:
        print_error(f"Failed to list cases: {e}")
        sys.exit(1)


@cases.command()
@click.argument("case_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get(ctx, case_id, output_json):
    """Get case details.

    Examples:
        scambus cases get <case-id>
    """
    client = ctx.obj.get_client()

    try:
        case = client.get_case(case_id)

        if output_json:
            print_json(
                {
                    "id": case.id,
                    "title": case.title,
                    "description": case.description,
                    "status": case.status,
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                }
            )
        else:
            print_detail(
                {
                    "ID": case.id,
                    "Title": case.title,
                    "Description": case.description or "N/A",
                    "Status": case.status or "N/A",
                    "Created": case.created_at.isoformat() if case.created_at else "N/A",
                },
                title="Case Details",
            )

    except Exception as e:
        print_error(f"Failed to get case: {e}")
        sys.exit(1)


@cases.command()
@click.option("--title", required=True, help="Case title")
@click.option("--description", help="Case description")
@click.option("--status", default="open", help="Case status (default: open)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(ctx, title, description, status, output_json):
    """Create a new case.

    Examples:
        scambus cases create --title "Phishing Campaign" --description "..."
    """
    client = ctx.obj.get_client()

    try:
        case = client.create_case(title=title, notes=description, status=status)

        if output_json:
            print_json(
                {
                    "id": case.id,
                    "title": case.title,
                    "status": case.status,
                }
            )
        else:
            print_success(f"Case created: {case.id}")
            print_detail(
                {
                    "ID": case.id,
                    "Title": case.title,
                    "Status": case.status,
                },
                title="Created Case",
            )

    except Exception as e:
        print_error(f"Failed to create case: {e}")
        sys.exit(1)


@cases.command()
@click.argument("case_id")
@click.option("--title", help="New title")
@click.option("--description", help="New description")
@click.option("--status", help="New status")
@click.pass_context
def update(ctx, case_id, title, description, status):
    """Update a case.

    Examples:
        scambus cases update <case-id> --status resolved
        scambus cases update <case-id> --title "New Title"
    """
    client = ctx.obj.get_client()

    try:
        updates = {}
        if title:
            updates["title"] = title
        if description:
            updates["notes"] = description
        if status:
            updates["status"] = status

        if not updates:
            print_error("No updates specified")
            sys.exit(1)

        case = client.update_case(case_id, **updates)
        print_success(f"Case updated: {case.id}")

    except Exception as e:
        print_error(f"Failed to update case: {e}")
        sys.exit(1)
