#!/usr/bin/env python3
"""
Views (Saved Queries) Example

This example demonstrates how to create, list, and execute saved query views.
Views allow you to save common search criteria and execute them repeatedly.
"""

import os
from scambus_client import (
    ScambusClient,
    FilterCriteria,
    IdentifierType,
    JournalEntryType,
    ViewSortOrder,
)

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

    # Using FilterCriteria and ViewSortOrder classes (recommended)
    view = client.create_view(
        name="High Confidence Phone Scams",
        entity_type="journal",
        filter_criteria=FilterCriteria(
            min_confidence=0.9,
            types=[JournalEntryType.DETECTION, JournalEntryType.PHONE_CALL],
            identifier_type=IdentifierType.PHONE,
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

    # FilterCriteria also works (all 60+ filter fields available)
    view2 = client.create_view(
        name="Recent Email Phishing",
        entity_type="journal",
        filter_criteria=FilterCriteria(
            min_confidence=0.8,
            types=[JournalEntryType.EMAIL],
            identifier_type=IdentifierType.EMAIL,
        ),
        sort_order=ViewSortOrder(field="performed_at", direction="desc"),
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
    filter1 = FilterCriteria(
        min_confidence=0.8,
        max_confidence=1.0,
    )
    print("\n1. Confidence range filter:")
    print(f"   {filter1.to_dict()}")

    # Filter by entry types
    filter2 = FilterCriteria(
        types=[JournalEntryType.DETECTION, JournalEntryType.PHONE_CALL, JournalEntryType.EMAIL],
    )
    print("\n2. Entry types filter:")
    print(f"   {filter2.to_dict()}")

    # Filter by identifier type
    filter3 = FilterCriteria(
        identifier_type=IdentifierType.PHONE,
    )
    print("\n3. Identifier type filter:")
    print(f"   {filter3.to_dict()}")

    # Combined filter
    filter4 = FilterCriteria(
        min_confidence=0.9,
        types=[JournalEntryType.DETECTION],
        identifier_type=IdentifierType.PHONE,
    )
    print("\n4. Combined filter:")
    print(f"   {filter4.to_dict()}")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see filter examples:
        # view_filter_examples()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
