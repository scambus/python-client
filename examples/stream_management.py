"""
Example: Export Stream Management with Scambus Client

This example demonstrates how to create and manage export streams using the
Scambus Python client library. This is for stream *owners* who create and
configure streams. For consuming a stream, see consumer_polling_example.py
and consumer_sse_example.py.

Export streams allow you to deliver real-time threat intelligence (journal entries
and identifier state changes) to consumers who subscribe with a consumer key.
"""

import os
from scambus_client import ScambusClient, FilterCriteria, IdentifierType, StreamDataType

# Initialize the client
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN")

client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_phone_stream_example():
    """Create a stream for high-confidence phone number journal entries."""
    stream = client.create_stream(
        name="High-Confidence Phone Numbers",
        data_type=StreamDataType.JOURNAL_ENTRY,
        filter_criteria=FilterCriteria(
            identifier_type=IdentifierType.PHONE,
            min_confidence=0.7,
            max_confidence=1.0,
        ),
        is_active=True,
        retention_days=90,
    )

    print(f"Created journal entry stream: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Consumer Key: {stream.consumer_key}")
    print(f"  Retention: {stream.retention_days} days")
    print(f"\n  Give the consumer key to external consumers.")

    return stream


def create_identifier_stream_example():
    """Create an identifier-centric stream with backfill."""
    stream = client.create_stream(
        name="All High-Confidence Identifiers",
        data_type=StreamDataType.IDENTIFIER,
        filter_criteria=FilterCriteria(
            min_confidence=0.9,
            max_confidence=1.0,
        ),
        is_active=True,
        retention_days=30,
        backfill_historical=True,
        backfill_from_date="2025-01-01T00:00:00Z",
    )

    print(f"\nCreated identifier stream with backfill: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Backfill: Starting from 2025-01-01")

    return stream


def consume_stream_example(consumer_key: str):
    """Consume messages from a stream using the consumer key."""
    result = client.consume_stream(
        stream_id=consumer_key,
        cursor="0",      # Start from beginning
        order="asc",     # Oldest first
        limit=10,
    )

    messages = result["messages"]
    next_cursor = result["next_cursor"]
    has_more = result["has_more"]

    print(f"\nConsumed {len(messages)} messages:")
    for msg in messages:
        if "identifier_id" in msg:
            print(f"  - Identifier: {msg['type']} = {msg['display_value']}")
        else:
            print(f"  - Entry: {msg['type']} - {msg.get('description', '')[:50]}")

    print(f"\n  Next cursor: {next_cursor}")
    print(f"  Has more: {has_more}")

    return next_cursor


def get_stream_info_example(consumer_key: str):
    """Get stream metadata from the consumer endpoint."""
    info = client.get_stream_info(consumer_key)

    print(f"\nStream Info:")
    print(f"  Name: {info.get('name')}")
    print(f"  Data Type: {info.get('data_type')}")
    print(f"  Messages: {info.get('messages_in_stream')}")
    print(f"  Rate Limit: {info.get('rate_limit_per_minute')}/min")


def main():
    """Run the stream management examples."""
    print("=== Export Stream Management Examples ===\n")

    # Create streams
    phone_stream = create_phone_stream_example()
    identifier_stream = create_identifier_stream_example()

    # Consume using the consumer key
    consumer_key = phone_stream.consumer_key or phone_stream.id
    consume_stream_example(consumer_key)

    # Get stream info via consumer endpoint
    get_stream_info_example(consumer_key)

    print("\n=== Examples Complete ===")
    print("\nNext steps:")
    print("1. Share the consumer key and API credentials with external consumers")
    print("2. Consumers can poll via consume_stream() or connect via SSE")
    print("3. See consumer_polling_example.py and consumer_sse_example.py")


if __name__ == "__main__":
    main()
