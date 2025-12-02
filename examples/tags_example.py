#!/usr/bin/env python3
"""
Tags Example

This example demonstrates how to work with tags:
- List available tags
- Create new tags
- Apply tags to journal entries using TagLookup
- Both boolean and valued tags
"""

import os
from scambus_client import ScambusClient, TagLookup

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate tag operations."""

    print("=" * 60)
    print("Tags Example")
    print("=" * 60)

    # =========================================================================
    # List Available Tags
    # =========================================================================
    print("\n1. Listing available tags...")

    tags = client.list_tags()
    print(f"   Found {len(tags)} tags")
    for tag in tags[:10]:
        tag_type = "valued" if tag.is_valued else "boolean"
        print(f"   - {tag.name} ({tag_type})")

    # =========================================================================
    # Create Boolean Tag
    # =========================================================================
    print("\n2. Creating a boolean tag...")

    # Boolean tags are simple flags (true/false)
    bool_tag = client.create_tag(
        name="HighPriority",
        description="Marks high priority items for immediate attention",
        is_valued=False,  # Boolean tag
    )
    print(f"   ✓ Created boolean tag: {bool_tag.name}")

    # =========================================================================
    # Create Valued Tag
    # =========================================================================
    print("\n3. Creating a valued tag...")

    # Valued tags can have associated values (like "ScamType:Phishing")
    valued_tag = client.create_tag(
        name="ScamCategory",
        description="Categorizes the type of scam",
        is_valued=True,  # Valued tag
    )
    print(f"   ✓ Created valued tag: {valued_tag.name}")

    # =========================================================================
    # Apply Tags to Journal Entry (Typed - Recommended)
    # =========================================================================
    print("\n4. Creating detection with typed TagLookup...")

    # Using TagLookup class (AWS CDK-style, recommended)
    entry = client.create_detection(
        description="Phishing email detected from fake bank",
        identifiers=[
            {"type": "email", "value": "scammer@fake-bank.com", "confidence": 0.95}
        ],
        tags=[
            TagLookup(tag_name="HighPriority"),  # Boolean tag
            TagLookup(tag_name="ScamCategory", tag_value="Phishing"),  # Valued tag
            TagLookup(tag_name="ScamCategory", tag_value="Banking"),  # Another value
        ],
    )

    print(f"   ✓ Created entry with tags: {entry.id}")

    # =========================================================================
    # Apply Tags to Journal Entry (Dictionary - Alternative)
    # =========================================================================
    print("\n5. Creating detection with dictionary tags...")

    # Dictionary format also works (backward compatible)
    entry2 = client.create_detection(
        description="Tech support scam call",
        identifiers=[
            {"type": "phone", "value": "+18005551234", "confidence": 0.9}
        ],
        tags=[
            {"tag_name": "HighPriority"},  # Boolean tag
            {"tag_name": "ScamCategory", "tag_value": "TechSupport"},  # Valued tag
        ],
    )

    print(f"   ✓ Created entry with tags: {entry2.id}")

    # =========================================================================
    # Get Effective Tags for Entity
    # =========================================================================
    print("\n6. Getting effective tags for an identifier...")

    # Get tags that apply to a specific entity
    if entry.identifiers:
        identifier_id = entry.identifiers[0].id
        effective_tags = client.get_effective_tags(
            entity_type="identifier",
            entity_id=identifier_id
        )
        print(f"   Effective tags for identifier {identifier_id}:")
        for tag in effective_tags:
            if tag.get("value"):
                print(f"   - {tag['name']}: {tag['value']}")
            else:
                print(f"   - {tag['name']}")

    # =========================================================================
    # Tag Management
    # =========================================================================
    print("\n7. Tag management operations...")

    # Get tag details
    tag_details = client.get_tag(bool_tag.id)
    print(f"   Tag: {tag_details.name}")
    print(f"   Description: {tag_details.description}")

    # Update tag
    updated_tag = client.update_tag(
        bool_tag.id,
        description="Updated description for high priority items"
    )
    print(f"   ✓ Updated tag description")

    # =========================================================================
    # Cleanup
    # =========================================================================
    print("\n8. Cleaning up...")

    # Delete the tags we created (optional)
    # Note: You may not be able to delete tags that are in use
    try:
        client.delete_tag(bool_tag.id)
        print(f"   ✓ Deleted tag: {bool_tag.name}")
    except Exception as e:
        print(f"   ! Could not delete tag (may be in use): {e}")

    try:
        client.delete_tag(valued_tag.id)
        print(f"   ✓ Deleted tag: {valued_tag.name}")
    except Exception as e:
        print(f"   ! Could not delete tag (may be in use): {e}")

    print("\n✓ Tags example completed!")


def tag_lookup_examples():
    """
    Examples of TagLookup usage patterns.
    """
    print("\n" + "=" * 60)
    print("TagLookup Examples")
    print("=" * 60)

    # Boolean tag
    print("\n1. Boolean tag (no value):")
    tag1 = TagLookup(tag_name="Verified")
    print(f"   {tag1}")

    # Valued tag
    print("\n2. Valued tag:")
    tag2 = TagLookup(tag_name="ScamType", tag_value="Phishing")
    print(f"   {tag2}")

    # Multiple values for same tag
    print("\n3. Multiple values for same tag:")
    tags = [
        TagLookup(tag_name="Industry", tag_value="Banking"),
        TagLookup(tag_name="Industry", tag_value="Finance"),
        TagLookup(tag_name="Industry", tag_value="Insurance"),
    ]
    for tag in tags:
        print(f"   {tag}")

    # Mixed tags in a list
    print("\n4. Mixed tags for journal entry:")
    mixed_tags = [
        TagLookup(tag_name="HighPriority"),  # Boolean
        TagLookup(tag_name="ScamType", tag_value="Phishing"),  # Valued
        TagLookup(tag_name="Region", tag_value="US"),  # Valued
    ]
    for tag in mixed_tags:
        print(f"   {tag}")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see TagLookup examples:
        # tag_lookup_examples()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
