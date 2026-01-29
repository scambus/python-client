"""Automation management commands."""

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
def automations():
    """Manage automations and API keys."""
    pass


@automations.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_automations(ctx, output_json):
    """List all automations.

    Examples:
        scambus automations list
        scambus automations list --json
    """
    client = ctx.obj.get_client()

    try:
        automation_list = client.list_automations()

        if not automation_list:
            print_info("No automations found")
            return

        if output_json:
            print_json(automation_list)
        else:
            table_data = [
                {
                    "ID": auto.get("id", "")[:8],
                    "Name": auto.get("name", "N/A"),
                    "Active": "Yes" if auto.get("active") else "No",
                    "Created": (
                        auto.get("created_at", "N/A")[:10] if auto.get("created_at") else "N/A"
                    ),
                }
                for auto in automation_list
            ]
            print_table(table_data, title=f"Automations ({len(automation_list)})")

    except Exception as e:
        print_error(f"Failed to list automations: {e}")
        sys.exit(1)


@automations.command("create")
@click.option("--name", required=True, help="Automation name")
@click.option("--description", help="Automation description")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create_automation(ctx, name, description, output_json):
    """Create a new automation.

    Examples:
        scambus automations create --name "My Bot"
        scambus automations create --name "Phishing Detector" --description "Automated detection"
    """
    client = ctx.obj.get_client()

    try:
        automation = client.create_automation(name=name, description=description)

        if output_json:
            print_json(automation)
        else:
            print_success(f"Automation created: {automation['id']}")
            details = {
                "ID": automation["id"],
                "Name": automation["name"],
                "Active": "Yes" if automation.get("active") else "No",
            }
            if automation.get("description"):
                details["Description"] = automation["description"]
            print_detail(details, title="Created Automation")

    except Exception as e:
        print_error(f"Failed to create automation: {e}")
        sys.exit(1)


@automations.command("create-key")
@click.argument("automation_name_or_id")
@click.option("--name", help="API key name (default: '<Automation Name> CLI Key')")
@click.option(
    "--assume",
    "assume_identity",
    is_flag=True,
    help="Switch to this automation identity after creating key",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def create_api_key(ctx, automation_name_or_id, name, assume_identity, output_json):
    """Create a new API key for an automation.

    Accepts either automation name or UUID. If using a name and the automation
    doesn't exist, it will fail (use 'scambus automations create' first).

    Examples:
        # Create key by UUID
        scambus automations create-key abc-123 --name "Production Key"

        # Create key by name
        scambus automations create-key "My Bot" --name "Dev Key"

        # Create key and immediately switch to it
        scambus automations create-key "My Bot" --assume
    """
    from scambus_cli.auth_device import DeviceAuthManager
    from scambus_cli.config import get_api_url

    client = ctx.obj.get_client()

    try:
        # Check if input looks like a UUID
        import re

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
        )
        is_uuid = bool(uuid_pattern.match(automation_name_or_id))

        if is_uuid:
            # Input is a UUID - use it directly
            automation_id = automation_name_or_id
            # Get automation name for key name
            automation = client.get_automation(automation_id)
            automation_name = automation.get("name", "Automation")
        else:
            # Input is a name - search for it
            automation_name = automation_name_or_id
            automations = client.list_automations()

            # Find all automations matching the name
            matching_automations = [
                auto for auto in automations if auto.get("name") == automation_name
            ]

            if len(matching_automations) == 0:
                print_error(f"Automation not found: {automation_name}")
                print_info(
                    'Create it first with: scambus automations create --name "{}"'.format(
                        automation_name
                    )
                )
                sys.exit(1)
            elif len(matching_automations) > 1:
                print_error(f"Multiple automations found with name: {automation_name}")
                print_info("\nAmbiguous automation name. Please use UUID instead:\n")
                table_data = [
                    {
                        "ID": auto.get("id", ""),
                        "Name": auto.get("name", "N/A"),
                        "Created": (
                            auto.get("created_at", "N/A")[:10] if auto.get("created_at") else "N/A"
                        ),
                    }
                    for auto in matching_automations
                ]
                print_table(table_data, title="Matching Automations")
                print_info('\nExample: scambus automations create-key <UUID> --name "Key Name"')
                sys.exit(1)

            automation_id = matching_automations[0]["id"]

        # Default key name if not provided
        if not name:
            name = f"{automation_name} CLI Key"

        # Create the API key
        key_data = client.create_automation_api_key(automation_id, name)

        access_key_id = key_data["accessKeyId"]
        secret_access_key = key_data["secretAccessKey"]
        combined_key = f"{access_key_id}:{secret_access_key}"

        if output_json:
            print_json(
                {
                    "apiKey": key_data["apiKey"],
                    "accessKeyId": access_key_id,
                    "secretAccessKey": secret_access_key,
                    "combinedKey": combined_key,
                }
            )
        else:
            print_success("API key created")
            print_info(f"\n⚠ Save this API key - it won't be shown again:\n{combined_key}\n")

        # If --assume flag is set, switch to this automation identity
        if assume_identity:
            print_info("Switching to automation identity...")
            api_url = get_api_url()
            manager = DeviceAuthManager(api_url)
            token = manager.api_key_login(combined_key)

            if token:
                print_success(f"Now operating as automation: {automation_name}")
            else:
                print_error("Failed to switch to automation identity")
                sys.exit(1)

    except Exception as e:
        print_error(f"Failed to create API key: {e}")
        sys.exit(1)


@automations.command("list-keys")
@click.argument("automation_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_api_keys(ctx, automation_id, output_json):
    """List API keys for an automation.

    Examples:
        scambus automations list-keys abc-123
    """
    client = ctx.obj.get_client()

    try:
        keys = client.list_automation_api_keys(automation_id)

        if not keys:
            print_info("No API keys found")
            return

        if output_json:
            print_json(keys)
        else:
            table_data = [
                {
                    "ID": key.get("id", "")[:8],
                    "Name": key.get("name", "N/A"),
                    "Created": (
                        key.get("created_at", "N/A")[:10] if key.get("created_at") else "N/A"
                    ),
                    "Revoked": "Yes" if key.get("revoked") else "No",
                }
                for key in keys
            ]
            print_table(table_data, title=f"API Keys ({len(keys)})")

    except Exception as e:
        print_error(f"Failed to list API keys: {e}")
        sys.exit(1)


@automations.command("revoke-key")
@click.argument("automation_id")
@click.argument("key_id")
@click.pass_context
def revoke_api_key(ctx, automation_id, key_id):
    """Revoke an API key.

    Examples:
        scambus automations revoke-key abc-123 key-456
    """
    client = ctx.obj.get_client()

    try:
        client.revoke_automation_api_key(automation_id, key_id)
        print_success(f"API key revoked: {key_id}")

    except Exception as e:
        print_error(f"Failed to revoke API key: {e}")
        sys.exit(1)


@automations.command("delete-key")
@click.argument("automation_id")
@click.argument("key_id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_api_key(ctx, automation_id, key_id, yes):
    """Delete an API key permanently.

    Examples:
        scambus automations delete-key abc-123 key-456
        scambus automations delete-key abc-123 key-456 --yes
    """
    if not yes:
        click.confirm(f"Are you sure you want to delete API key {key_id}?", abort=True)

    client = ctx.obj.get_client()

    try:
        client.delete_automation_api_key(automation_id, key_id)
        print_success(f"API key deleted: {key_id}")

    except Exception as e:
        print_error(f"Failed to delete API key: {e}")
        sys.exit(1)
