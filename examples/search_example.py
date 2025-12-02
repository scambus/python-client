#!/usr/bin/env python3
"""
Search Example

This example demonstrates the search functionality:
- Search identifiers by value or type
- Search cases by title or status
- Query journal entries with filters
"""

import os
from scambus_client import ScambusClient

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate search operations."""

    print("=" * 60)
    print("Search Example")
    print("=" * 60)

    # =========================================================================
    # Search Identifiers
    # =========================================================================
    print("\n1. Searching identifiers...")

    # Search by value
    print("\n   a) Search by phone number:")
    results = client.search_identifiers(query="+1234567890")
    print(f"      Found {len(results)} identifiers")
    for identifier in results[:3]:
        print(f"      - {identifier.type}: {identifier.display_value} "
              f"(confidence: {identifier.confidence})")

    # Search by email domain
    print("\n   b) Search by email domain:")
    results = client.search_identifiers(
        query="@suspicious-domain.com",
        identifier_type="email"
    )
    print(f"      Found {len(results)} email identifiers")

    # Search by type only
    print("\n   c) List phone identifiers:")
    results = client.search_identifiers(
        identifier_type="phone",
        limit=5
    )
    print(f"      Found {len(results)} phone identifiers")
    for identifier in results[:3]:
        print(f"      - {identifier.display_value} (confidence: {identifier.confidence})")

    # =========================================================================
    # List Identifiers
    # =========================================================================
    print("\n2. Listing identifiers with filters...")

    identifiers = client.list_identifiers(
        identifier_type="email",
        min_confidence=0.8,
        limit=10
    )
    print(f"   Found {len(identifiers)} high-confidence email identifiers")
    for identifier in identifiers[:3]:
        print(f"   - {identifier.display_value}")

    # =========================================================================
    # Search Cases
    # =========================================================================
    print("\n3. Searching cases...")

    # Search by title/description
    print("\n   a) Search cases by keyword:")
    cases = client.search_cases(query="phishing")
    print(f"      Found {len(cases)} cases matching 'phishing'")
    for case in cases[:3]:
        print(f"      - {case.title} ({case.status})")

    # Search by status
    print("\n   b) Search open cases:")
    open_cases = client.search_cases(status="open")
    print(f"      Found {len(open_cases)} open cases")

    # Combined search
    print("\n   c) Search open cases about fraud:")
    fraud_cases = client.search_cases(
        query="fraud",
        status="open",
        limit=5
    )
    print(f"      Found {len(fraud_cases)} matching cases")

    # =========================================================================
    # Query Journal Entries
    # =========================================================================
    print("\n4. Querying journal entries...")

    # Basic search
    print("\n   a) Search journal entries by keyword:")
    entries = client.query_journal_entries(
        search_query="suspicious",
        limit=10
    )
    print(f"      Found {len(entries)} entries")

    # Filter by entry type
    print("\n   b) Search phone call entries:")
    phone_entries = client.query_journal_entries(
        entry_type="phone_call",
        limit=5
    )
    print(f"      Found {len(phone_entries)} phone call entries")

    # Filter by confidence
    print("\n   c) Search high-confidence detections:")
    detections = client.query_journal_entries(
        entry_type="detection",
        min_confidence=0.9,
        limit=5
    )
    print(f"      Found {len(detections)} high-confidence detections")
    for entry in detections[:3]:
        print(f"      - {entry.description[:50]}...")

    # Filter by date range
    print("\n   d) Search entries from specific date range:")
    recent_entries = client.query_journal_entries(
        performed_after="2025-01-01T00:00:00Z",
        performed_before="2025-12-31T23:59:59Z",
        limit=5
    )
    print(f"      Found {len(recent_entries)} entries in 2025")

    # Combined filters
    print("\n   e) Combined filters:")
    filtered_entries = client.query_journal_entries(
        search_query="scam",
        entry_type="phone_call",
        min_confidence=0.8,
        performed_after="2025-01-01T00:00:00Z",
        limit=10
    )
    print(f"      Found {len(filtered_entries)} matching entries")

    print("\n✓ Search example completed!")


def search_patterns():
    """
    Common search patterns and use cases.
    """
    print("\n" + "=" * 60)
    print("Common Search Patterns")
    print("=" * 60)

    # Pattern 1: Find all reports for a specific phone number
    print("\n1. Find all reports for a phone number:")
    print("   results = client.search_identifiers(query='+18005551234')")
    print("   for identifier in results:")
    print("       # Get journal entries linked to this identifier")
    print("       entries = client.query_journal_entries(identifier_id=identifier.id)")

    # Pattern 2: Find high-confidence scams by type
    print("\n2. Find high-confidence email scams:")
    print("   entries = client.query_journal_entries(")
    print("       entry_type='email',")
    print("       min_confidence=0.9,")
    print("       limit=100")
    print("   )")

    # Pattern 3: Find open investigations
    print("\n3. Find open investigations with activity:")
    print("   cases = client.search_cases(status='open')")
    print("   for case in cases:")
    print("       # Get journal entries linked to case")
    print("       entries = client.list_journal_entries(case_id=case.id)")

    # Pattern 4: Search across multiple identifier types
    print("\n4. Search for related identifiers:")
    print("   emails = client.search_identifiers(query='scammer.com', identifier_type='email')")
    print("   phones = client.search_identifiers(query='+1800', identifier_type='phone')")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see search patterns:
        # search_patterns()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
