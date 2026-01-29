"""
Example: Export Stream Management with Scambus Client

This example demonstrates how to create and manage export streams using the
Scambus Python client library.

Export streams allow you to receive real-time notifications of journal entries
and identifiers that match specific criteria (e.g., phone numbers with confidence > 0.7).
"""

import os
from scambus_client import ScambusClient

# Initialize the client
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN")

client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_phone_stream_example():
    """Create a stream for high-confidence phone number journal entries."""
    stream = client.create_stream(
        name="High-Confidence Phone Numbers",
        data_type="journal_entry",
        identifier_types=["phone"],
        min_confidence=0.7,
        max_confidence=1.0,
        is_active=True,
        retention_days=90,
    )

    print(f"✓ Created journal entry stream: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Types: {stream.identifier_types}")
    print(f"  Confidence: {stream.min_confidence} - {stream.max_confidence}")
    print(f"  Consumer Key: {stream.consumer_key}")
    print(f"  Retention: {stream.retention_days} days")

    return stream.id


def create_identifier_stream_example():
    """Create an identifier-centric stream with backfill."""
    stream = client.create_stream(
        name="All High-Confidence Identifiers",
        data_type="identifier",
        identifier_types=[],  # All types
        min_confidence=0.9,
        max_confidence=1.0,
        is_active=True,
        retention_days=30,
        backfill_historical=True,  # Backfill existing identifiers
        backfill_from_date="2025-01-01T00:00:00Z",  # Only from this date
    )

    print(f"\n✓ Created identifier stream with backfill: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Confidence: {stream.min_confidence} - {stream.max_confidence}")
    print(f"  Backfill: Starting from 2025-01-01")

    return stream.id


def list_streams_example():
    """List all export streams."""
    streams = client.list_streams()

    print(f"\n✓ Found {len(streams)} streams:")
    for stream in streams:
        active = "active" if stream.is_active else "inactive"
        types = ", ".join(stream.identifier_types) if stream.identifier_types else "all types"
        print(f"  - {stream.name} ({stream.data_type}, {types}, {active})")


def get_stream_details(stream_id: str):
    """Get detailed information about a stream."""
    stream = client.get_stream(stream_id)

    print(f"\n✓ Stream Details:")
    print(f"  ID: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Identifier Types: {stream.identifier_types or 'all'}")
    print(f"  Confidence Range: {stream.min_confidence} - {stream.max_confidence}")
    print(f"  Active: {stream.is_active}")
    print(f"  Consumer Key: {stream.consumer_key}")
    print(f"  Retention: {stream.retention_days} days")
    print(f"  Created: {stream.created_at}")


def consume_stream_example(stream_id: str):
    """Consume messages from a stream."""
    # Consume from the beginning
    result = client.consume_stream(
        stream_id=stream_id,
        cursor="0",  # Start from beginning
        order="asc",  # Oldest first
        limit=10,  # Get 10 messages
    )

    messages = result.get("messages", [])
    next_cursor = result.get("nextCursor")

    print(f"\n✓ Consumed {len(messages)} messages:")
    for msg in messages:
        if "displayValue" in msg:
            # Identifier message
            print(f"  - Identifier: {msg.get('type')} = {msg.get('displayValue')}")
        else:
            # Journal entry message
            print(f"  - Entry: {msg.get('type')} - {msg.get('description', '')[:50]}")

    print(f"\n  Next cursor: {next_cursor}")

    return next_cursor


def recover_stream_example(stream_id: str):
    """Recover/rebuild a stream to fix gaps or corruption."""
    result = client.recover_stream(
        stream_id=stream_id,
        ignore_checkpoint=False,  # Use checkpoint
        clear_stream=True,  # Clear and rebuild
    )

    print(f"\n✓ Recovery Status:")
    print(f"  Stream: {result.get('stream_name')}")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message')}")


def get_recovery_info(stream_id: str):
    """Get recovery information for a stream."""
    info = client.get_stream_recovery_info(stream_id)

    print(f"\n✓ Recovery Information:")
    print(f"  Is Rebuilding: {info.get('isRebuilding')}")
    print(f"  Last Consumed Entry: {info.get('lastConsumedJournalEntry', 'None')}")
    print(f"  Entries to Replay: {info.get('journalEntriesToReplay', 0)}")


def backfill_stream_example(stream_id: str):
    """Trigger backfill for an identifier-centric stream."""
    # Only works for identifier-centric streams
    result = client.backfill_stream(
        stream_id=stream_id,
        from_date="2025-01-01T00:00:00Z",  # Optional: only backfill from this date
    )

    print(f"\n✓ Backfill Status:")
    print(f"  Status: {result.get('status')}")
    print(f"  Message: {result.get('message')}")


def main():
    """Run the stream management examples."""
    print("=== Export Stream Management Examples ===\n")

    # Create a journal entry stream
    phone_stream_id = create_phone_stream_example()

    # Create an identifier stream with backfill
    identifier_stream_id = create_identifier_stream_example()

    # List all streams
    list_streams_example()

    # Get detailed stream information
    get_stream_details(phone_stream_id)

    # Consume messages from the stream
    next_cursor = consume_stream_example(phone_stream_id)

    # Get recovery information
    get_recovery_info(phone_stream_id)

    # Trigger recovery if needed (commented out by default)
    # recover_stream_example(phone_stream_id)

    # Trigger backfill for identifier stream (commented out by default)
    # backfill_stream_example(identifier_stream_id)

    print("\n=== Examples Complete ===")
    print("\nNext steps:")
    print("1. Use the consumer key to subscribe to the stream")
    print("2. Messages will be delivered in real-time as new data arrives")
    print("3. Use the cursor to track your position and resume from where you left off")


if __name__ == "__main__":
    main()
