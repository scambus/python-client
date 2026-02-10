"""
Example: Identifier Stream Usage with Scambus Client

This example demonstrates how to create and consume identifier-centric streams.
Identifier streams publish identifier state changes (confidence, tags, type) rather
than journal entries, providing a different view of your data.

Key differences from journal entry streams:
- Data Type: "identifier" instead of "journal_entry"
- Events: Identifier state changes rather than journal entries
- Use Case: Track how specific identifiers evolve over time
- Backfill: Can backfill historical identifier states
"""

import os
import time
from scambus_client import ScambusClient, FilterCriteria, IdentifierType, StreamDataType

# Initialize the client
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN")

client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_identifier_stream_basic():
    """Create a basic identifier stream for all high-confidence identifiers."""
    stream = client.create_stream(
        name="High-Confidence Identifiers",
        data_type=StreamDataType.IDENTIFIER,
        filter_criteria=FilterCriteria(
            min_confidence=0.9,
            max_confidence=1.0,
        ),
        is_active=True,
        retention_days=30,
    )

    print(f"Created identifier stream: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Consumer Key: {stream.consumer_key}")

    return stream


def create_identifier_stream_with_backfill():
    """Create an identifier stream with historical backfill."""
    stream = client.create_stream(
        name="Recent Email Identifiers",
        data_type=StreamDataType.IDENTIFIER,
        filter_criteria=FilterCriteria(
            identifier_type=IdentifierType.EMAIL,
            min_confidence=0.7,
            max_confidence=1.0,
        ),
        is_active=True,
        retention_days=30,
        backfill_historical=True,
        backfill_from_date="2025-01-01T00:00:00Z",
    )

    print(f"\nCreated identifier stream with backfill: {stream.id}")
    print(f"  Backfill: Triggered from 2025-01-01")

    return stream


def consume_identifier_stream(consumer_key: str):
    """Consume identifier state changes from a stream."""
    print(f"\nConsuming identifier stream: {consumer_key}")

    result = client.consume_stream(
        stream_id=consumer_key,
        cursor="0",
        order="asc",
        limit=10,
    )

    messages = result["messages"]
    next_cursor = result["next_cursor"]
    has_more = result["has_more"]

    print(f"  Received {len(messages)} messages (has_more={has_more})")

    for i, msg in enumerate(messages, 1):
        print(f"\n  --- Message {i} ---")
        print(f"  Identifier ID: {msg.get('identifier_id')}")
        print(f"  Type: {msg.get('type')}")
        print(f"  Value: {msg.get('display_value')}")
        print(f"  Confidence: {msg.get('confidence')}")

        # Show structured data (type-specific details)
        details = msg.get("details", {})
        if details and msg.get("type") == "phone":
            print(f"  Country Code: {details.get('country_code')}")
            print(f"  Number: {details.get('number')}")
            if details.get("area_code"):
                print(f"  Area Code: {details.get('area_code')}")
            print(f"  Toll-Free: {details.get('is_toll_free', False)}")
            if details.get("region"):
                print(f"  Region: {details.get('region')}")

        # Show tags
        for tag in msg.get("tags", []):
            print(f"  Tag: {tag.get('tag_title')}: {tag.get('value')}")

        # Show triggering journal entry
        tje = msg.get("triggering_journal_entry")
        if tje:
            print(f"  Triggered by: {tje.get('type')} at {tje.get('performed_at')}")

    if next_cursor:
        print(f"\n  Next cursor: {next_cursor}")

    return next_cursor


def continuous_consumption_example(consumer_key: str, duration_seconds: int = 30):
    """Example of continuous stream consumption (polling)."""
    print(f"\nStarting continuous consumption for {duration_seconds} seconds...")

    cursor = "0"
    start_time = time.time()
    total_messages = 0

    while time.time() - start_time < duration_seconds:
        result = client.consume_stream(
            stream_id=consumer_key,
            cursor=cursor,
            order="asc",
            limit=100,
        )

        messages = result["messages"]

        if messages:
            total_messages += len(messages)
            print(f"  Received {len(messages)} identifier state changes")

            for msg in messages:
                identifier_type = msg.get("type")
                display_value = msg.get("display_value")
                confidence = msg.get("confidence", 0)
                print(f"    - {identifier_type}: {display_value} (confidence: {confidence})")

        # Advance cursor
        if result["next_cursor"]:
            cursor = result["next_cursor"]

        # If no more messages, wait before polling again
        if not result["has_more"]:
            time.sleep(1)

    print(f"\n  Total messages consumed: {total_messages}")


def comparison_example():
    """Show the key differences between journal entry and identifier streams."""
    print("\n" + "=" * 60)
    print("COMPARISON: Journal Entry vs Identifier Streams")
    print("=" * 60)

    print("""
    | Feature     | Journal Entry Stream    | Identifier Stream         |
    |-------------|-------------------------|---------------------------|
    | Data Type   | journal_entry           | identifier                |
    | Publishes   | Complete journal entries | Identifier state changes  |
    | Frequency   | Every matching JE       | Only on state change      |
    | Contains    | JE + identifiers + evid | Identifier + triggering JE|
    | Backfill    | Not supported           | Supported                 |
    | Use Case    | Track all scam events   | Track identifier evolution|
    """)


if __name__ == "__main__":
    print("=" * 60)
    print("Identifier Stream Examples")
    print("=" * 60)

    # Create streams
    stream = create_identifier_stream_basic()
    email_stream = create_identifier_stream_with_backfill()

    # Consume messages using consumer key
    consumer_key = stream.consumer_key or stream.id
    consume_identifier_stream(consumer_key)

    # Continuous consumption (uncomment to run)
    # continuous_consumption_example(consumer_key, duration_seconds=30)

    # Show comparison
    comparison_example()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
