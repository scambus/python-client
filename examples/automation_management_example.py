#!/usr/bin/env python3
"""
Automation Management Example

This example demonstrates how to create and manage automation identities
with API key support for programmatic access.

Use automations for:
- CI/CD pipelines
- Scheduled scripts
- Bot accounts
- Service integrations
"""

import os
from scambus_client import ScambusClient

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client (as your personal account)
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate automation management operations."""

    print("=" * 60)
    print("Automation Management Example")
    print("=" * 60)

    # =========================================================================
    # List Existing Automations
    # =========================================================================
    print("\n1. Listing existing automations...")

    automations = client.list_automations()
    print(f"   Found {len(automations)} automations")
    for automation in automations[:5]:
        print(f"   - {automation.get('name')} ({automation.get('id')[:8]}...)")

    # =========================================================================
    # Create New Automation
    # =========================================================================
    print("\n2. Creating new automation...")

    automation = client.create_automation(
        name="Phishing Detector Bot",
        description="Automated phishing detection and reporting"
    )

    automation_id = automation.get("id")
    print(f"   ✓ Created automation: {automation.get('name')}")
    print(f"     ID: {automation_id}")

    # =========================================================================
    # Create API Key for Automation
    # =========================================================================
    print("\n3. Creating API key for automation...")

    key_data = client.create_automation_api_key(
        automation_id=automation_id,
        name="Production Key"
    )

    access_key_id = key_data.get("accessKeyId")
    secret_key = key_data.get("secretAccessKey")
    api_key = f"{access_key_id}:{secret_key}"

    print(f"   ✓ Created API key")
    print(f"     Access Key ID: {access_key_id}")
    print(f"     Secret: {secret_key[:10]}...")
    print(f"\n   ⚠ SAVE THIS KEY - it won't be shown again!")
    print(f"   Full key: {api_key}")

    # =========================================================================
    # List API Keys for Automation
    # =========================================================================
    print("\n4. Listing API keys for automation...")

    keys = client.list_automation_api_keys(automation_id)
    print(f"   Found {len(keys)} API keys")
    for key in keys:
        status = "active" if key.get("isActive") else "revoked"
        print(f"   - {key.get('name')} ({status}) - {key.get('accessKeyId')[:8]}...")

    # =========================================================================
    # Create Additional Key (for rotation)
    # =========================================================================
    print("\n5. Creating additional key for rotation...")

    new_key_data = client.create_automation_api_key(
        automation_id=automation_id,
        name="Rotation Key"
    )
    new_key_id = new_key_data.get("accessKeyId")
    print(f"   ✓ Created new key: {new_key_id[:8]}...")

    # =========================================================================
    # Revoke Old Key
    # =========================================================================
    print("\n6. Revoking old key...")

    # Get the key ID from step 3
    old_key_id = access_key_id

    client.revoke_automation_api_key(automation_id, old_key_id)
    print(f"   ✓ Revoked key: {old_key_id[:8]}...")

    # Verify revocation
    keys = client.list_automation_api_keys(automation_id)
    for key in keys:
        if key.get("accessKeyId") == old_key_id:
            print(f"     Status: {'revoked' if not key.get('isActive') else 'still active'}")

    # =========================================================================
    # Delete Key Permanently
    # =========================================================================
    print("\n7. Deleting revoked key...")

    client.delete_automation_api_key(automation_id, old_key_id)
    print(f"   ✓ Deleted key: {old_key_id[:8]}...")

    # =========================================================================
    # Use Automation Client
    # =========================================================================
    print("\n8. Using automation credentials...")

    # Create a new client with automation credentials
    new_api_key = f"{new_key_data.get('accessKeyId')}:{new_key_data.get('secretAccessKey')}"

    # Note: In practice, you would use the API key like this:
    # automation_client = ScambusClient(api_key_id=access_key_id, api_key_secret=secret_key)

    print("   To use automation credentials in scripts:")
    print(f"   automation_client = ScambusClient(")
    print(f"       api_key_id='{new_key_data.get('accessKeyId')[:8]}...',")
    print(f"       api_key_secret='...'")
    print(f"   )")

    # =========================================================================
    # Cleanup
    # =========================================================================
    print("\n9. Cleaning up...")

    # Delete the remaining key
    client.delete_automation_api_key(automation_id, new_key_data.get("accessKeyId"))
    print(f"   ✓ Deleted remaining key")

    # Note: You may want to keep the automation for future use
    # To delete the automation itself:
    # client.delete_automation(automation_id)
    print(f"   Note: Automation '{automation.get('name')}' still exists")
    print(f"         Delete manually if not needed")

    print("\n✓ Automation management example completed!")


def key_rotation_workflow():
    """
    Demonstrates a complete key rotation workflow.
    """
    print("\n" + "=" * 60)
    print("Key Rotation Workflow")
    print("=" * 60)

    print("""
    Key rotation steps:

    1. Create new key (while old key still works):
       new_key = client.create_automation_api_key(automation_id, name="New Key")

    2. Update your scripts/services with new key:
       - Update environment variables
       - Update secrets management
       - Deploy changes

    3. Verify new key works:
       - Test authentication
       - Monitor for errors

    4. Revoke old key:
       client.revoke_automation_api_key(automation_id, old_key_id)

    5. (Optional) Delete old key after grace period:
       client.delete_automation_api_key(automation_id, old_key_id)

    CLI equivalent:
    ---------------
    # Create new key
    scambus automations create-key "Bot Name" --name "New Key"

    # Switch to new key immediately
    scambus automations create-key "Bot Name" --assume

    # Revoke old key
    scambus automations revoke-key AUTOMATION_ID OLD_KEY_ID

    # Delete old key
    scambus automations delete-key AUTOMATION_ID OLD_KEY_ID
    """)


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see key rotation workflow:
        # key_rotation_workflow()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
