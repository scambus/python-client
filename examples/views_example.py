#!/usr/bin/env python3
"""
Views (Saved Queries) Example

This example demonstrates how to create, list, and execute saved query views.
Views allow you to save common search criteria and execute them repeatedly.
"""

import os
from scambus_client import ScambusClient, ViewFilter, ViewSortOrder

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate view management operations."""

    print("=" * 60)
    print("Views (Saved Queries) Example")
    print("=" * 60)

    # =========================================================================
    # Execute System Views
    # =========================================================================
    print("\n1. Executing system views...")

    # My Journal - your recent journal entries
    print("\n  a) My Journal entries:")
    my_journal = client.execute_my_journal_entries(limit=5)
    entries = my_journal.get("data", [])
    print(f"     Found {len(entries)} entries")
    for entry in entries[:3]:
        print(f"     - {entry.get('type')}: {entry.get('description', '')[:50]}")

    # My Pinboard - pinned items
    print("\n  b) My Pinboard:")
    pinboard = client.execute_my_pinboard(limit=5)
    pinned = pinboard.get("data", [])
    print(f"     Found {len(pinned)} pinned items")

    # =========================================================================
    # List Custom Views
    # =========================================================================
    print("\n2. Listing custom views...")

    views = client.list_views()
    print(f"   Found {len(views)} views")
    for view in views[:5]:
        print(f"   - {view.name} ({view.entity_type})")

    # =========================================================================
    # Create Custom View with Typed Filters
    # =========================================================================
    print("\n3. Creating custom view with typed filters...")

    # Using ViewFilter and ViewSortOrder classes (recommended)
    view = client.create_view(
        name="High Confidence Phone Scams",
        entity_type="journal",
        filter_criteria=ViewFilter(
            min_confidence=0.9,
            entry_types=["detection", "phone_call"],
            identifier_types=["phone"],
        ),
        sort_order=ViewSortOrder(field="created_at", direction="desc"),
        visibility="private",  # or "organization"
    )

    print(f"   ✓ Created view: {view.id}")
    print(f"     Name: {view.name}")
    print(f"     Entity Type: {view.entity_type}")

    # =========================================================================
    # Create View with Dictionary Filters (Alternative)
    # =========================================================================
    print("\n4. Creating view with dictionary filters...")

    # Dictionary format also works (backward compatible)
    view2 = client.create_view(
        name="Recent Email Phishing",
        entity_type="journal",
        filter_criteria={
            "min_confidence": 0.8,
            "entry_types": ["email"],
            "identifier_types": ["email"],
        },
        sort_order={"field": "performed_at", "direction": "desc"},
        visibility="private",
    )

    print(f"   ✓ Created view: {view2.id}")

    # =========================================================================
    # Execute Custom View
    # =========================================================================
    print("\n5. Executing custom view...")

    result = client.execute_view(view.id, limit=10)
    entries = result.get("data", [])
    print(f"   Found {len(entries)} matching entries")
    for entry in entries[:3]:
        print(f"   - {entry.get('type')}: {entry.get('description', '')[:40]}...")

    # =========================================================================
    # Get View Details
    # =========================================================================
    print("\n6. Getting view details...")

    view_details = client.get_view(view.id)
    print(f"   Name: {view_details.name}")
    print(f"   Entity Type: {view_details.entity_type}")
    print(f"   Visibility: {view_details.visibility}")
    print(f"   Created: {view_details.created_at}")

    # =========================================================================
    # Delete Views (cleanup)
    # =========================================================================
    print("\n7. Cleaning up views...")

    client.delete_view(view.id)
    print(f"   ✓ Deleted view: {view.id}")

    client.delete_view(view2.id)
    print(f"   ✓ Deleted view: {view2.id}")

    print("\n✓ Views example completed!")


def view_filter_examples():
    """
    Examples of different ViewFilter configurations.
    """
    print("\n" + "=" * 60)
    print("ViewFilter Examples")
    print("=" * 60)

    # Filter by confidence range
    filter1 = ViewFilter(
        min_confidence=0.8,
        max_confidence=1.0,
    )
    print("\n1. Confidence range filter:")
    print(f"   {filter1}")

    # Filter by entry types
    filter2 = ViewFilter(
        entry_types=["detection", "phone_call", "email"],
    )
    print("\n2. Entry types filter:")
    print(f"   {filter2}")

    # Filter by identifier types
    filter3 = ViewFilter(
        identifier_types=["phone", "email"],
    )
    print("\n3. Identifier types filter:")
    print(f"   {filter3}")

    # Combined filter
    filter4 = ViewFilter(
        min_confidence=0.9,
        entry_types=["detection"],
        identifier_types=["phone"],
    )
    print("\n4. Combined filter:")
    print(f"   {filter4}")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see filter examples:
        # view_filter_examples()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
