"""Tag management commands."""

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
def tags():
    """Manage tags."""
    pass


@tags.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_tags(ctx, output_json):
    """List available tags.

    Examples:
        scambus tags list
    """
    client = ctx.obj.get_client()

    try:
        tag_list = client.list_tags()

        if not tag_list:
            print_info("No tags found")
            return

        if output_json:
            print_json(
                [
                    {
                        "id": t.id,
                        "name": t.name,
                        "type": t.type,
                        "created_at": (
                            t.created_at.isoformat()
                            if hasattr(t, "created_at") and t.created_at
                            else None
                        ),
                    }
                    for t in tag_list
                ]
            )
        else:
            table_data = [
                {
                    "ID": t.id[:8],
                    "Name": t.name,
                    "Type": t.type or "N/A",
                }
                for t in tag_list
            ]

            print_table(table_data, title=f"Tags ({len(tag_list)})")

    except Exception as e:
        print_error(f"Failed to list tags: {e}")
        sys.exit(1)


@tags.command()
@click.option("--name", required=True, help="Tag name")
@click.option("--type", "tag_type", required=True, help="Tag type")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create(ctx, name, tag_type, output_json):
    """Create a new tag.

    Examples:
        scambus tags create --name "High Priority" --type priority
    """
    client = ctx.obj.get_client()

    try:
        tag = client.create_tag(title=name, tag_type=tag_type)

        if output_json:
            print_json(
                {
                    "id": tag.id,
                    "name": tag.name,
                    "type": tag.type,
                }
            )
        else:
            print_success(f"Tag created: {tag.id}")
            print_detail(
                {
                    "ID": tag.id,
                    "Name": tag.name,
                    "Type": tag.type,
                },
                title="Created Tag",
            )

    except Exception as e:
        print_error(f"Failed to create tag: {e}")
        sys.exit(1)
