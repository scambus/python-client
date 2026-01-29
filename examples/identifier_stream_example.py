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
from scambus_client import ScambusClient

# Initialize the client
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN")

client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_identifier_stream_basic():
    """Create a basic identifier stream for all high-confidence identifiers."""
    stream = client.create_stream(
        name="High-Confidence Identifiers",
        data_type="identifier",  # KEY: Set to "identifier" for identifier streams
        min_confidence=0.9,
        max_confidence=1.0,
        is_active=True,
        retention_days=30,
    )

    print(f"✓ Created identifier stream: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Data Type: {stream.data_type}")
    print(f"  Confidence Range: {stream.min_confidence} - {stream.max_confidence}")
    print(f"  Consumer Key: {stream.consumer_key}")

    return stream.id


def create_identifier_stream_filtered():
    """Create an identifier stream filtered by type."""
    stream = client.create_stream(
        name="High-Confidence Phone Numbers",
        data_type="identifier",
        identifier_types=["phone"],  # Only phone identifiers
        min_confidence=0.8,
        max_confidence=1.0,
        is_active=True,
        retention_days=90,
    )

    print(f"\n✓ Created filtered identifier stream: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Identifier Types: {stream.identifier_types}")
    print(f"  Confidence Range: {stream.min_confidence} - {stream.max_confidence}")

    return stream.id


def create_identifier_stream_with_backfill():
    """Create an identifier stream with historical backfill."""
    stream = client.create_stream(
        name="Recent Email Identifiers",
        data_type="identifier",
        identifier_types=["email"],
        min_confidence=0.7,
        max_confidence=1.0,
        is_active=True,
        retention_days=30,
        backfill_historical=True,  # Trigger backfill on creation
        backfill_from_date="2025-01-01T00:00:00Z",  # Only backfill from this date
    )

    print(f"\n✓ Created identifier stream with backfill: {stream.id}")
    print(f"  Name: {stream.name}")
    print(f"  Identifier Types: {stream.identifier_types}")
    print(f"  Backfill: Triggered from 2025-01-01")

    return stream.id


def consume_identifier_stream(stream_id: str):
    """Consume identifier state changes from a stream."""
    print(f"\n✓ Consuming identifier stream: {stream_id}")

    # Start from the beginning
    cursor = "0"

    # Consume in pages
    result = client.consume_stream(
        stream_id=stream_id, cursor=cursor, order="asc", limit=10  # Oldest first
    )

    messages = result.get("messages", [])
    next_cursor = result.get("nextCursor")

    print(f"  Received {len(messages)} messages")
    if next_cursor:
        print(f"  Next cursor: {next_cursor}")

    # Process identifier messages
    for i, msg in enumerate(messages, 1):
        print(f"\n  --- Message {i} ---")
        print(f"  Identifier ID: {msg.get('identifierId', msg.get('identifier_id'))}")
        print(f"  Type: {msg.get('type')}")
        print(f"  Value: {msg.get('displayValue', msg.get('display_value'))}")
        print(f"  Confidence: {msg.get('confidence')}")
        print(f"  Published: {msg.get('publishedAt', msg.get('published_at'))}")

        # Show structured data (type-specific details)
        details = msg.get("details")
        if details:
            print(f"  Structured Data:")
            identifier_type = msg.get("type")

            if identifier_type == "phone":
                # Phone numbers include: country_code, number, area_code, is_toll_free, region
                print(
                    f"    Country Code: {details.get('country_code') or details.get('countryCode')}"
                )
                print(f"    Number: {details.get('number')}")
                if details.get("area_code") or details.get("areaCode"):
                    print(f"    Area Code: {details.get('area_code') or details.get('areaCode')}")
                print(
                    f"    Toll-Free: {details.get('is_toll_free', details.get('isTollFree', False))}"
                )
                if details.get("region"):
                    print(f"    Region: {details.get('region')}")

            elif identifier_type == "email":
                # Email includes: email
                print(f"    Email: {details.get('email')}")

            elif identifier_type == "bank_account":
                # Bank accounts include: account_number, routing, institution, etc.
                print(
                    f"    Account: {details.get('account_number') or details.get('accountNumber')}"
                )
                print(f"    Routing: {details.get('routing')}")
                if details.get("institution"):
                    print(f"    Institution: {details.get('institution')}")

            elif identifier_type == "crypto_wallet":
                # Crypto wallets include: address, currency, network
                print(f"    Address: {details.get('address')}")
                if details.get("currency"):
                    print(f"    Currency: {details.get('currency')}")
                if details.get("network"):
                    print(f"    Network: {details.get('network')}")

            elif identifier_type == "social_media":
                # Social media includes: platform, handle
                print(f"    Platform: {details.get('platform')}")
                print(f"    Handle: {details.get('handle')}")

            elif identifier_type == "zelle":
                # Zelle includes: type, value
                print(f"    Type: {details.get('type')}")
                print(f"    Value: {details.get('value')}")

        # Show tags
        tags = msg.get("tags", [])
        if tags:
            tag_names = [t.get("name", "unknown") for t in tags]
            print(f"  Tags: {', '.join(tag_names)}")

        # Show triggering journal entry
        triggering_je = msg.get("triggeringJournalEntry") or msg.get("triggering_journal_entry")
        if triggering_je:
            print(
                f"  Triggered by: {triggering_je.get('type')} at {triggering_je.get('performedAt', triggering_je.get('performed_at'))}"
            )

    return next_cursor


def continuous_consumption_example(stream_id: str, duration_seconds: int = 30):
    """Example of continuous stream consumption (polling)."""
    print(f"\n✓ Starting continuous consumption for {duration_seconds} seconds...")

    cursor = "0"
    start_time = time.time()
    total_messages = 0

    while time.time() - start_time < duration_seconds:
        result = client.consume_stream(
            stream_id=stream_id,
            cursor=cursor,
            order="asc",
            limit=100,
            timeout=5,  # Wait up to 5 seconds for new messages
        )

        messages = result.get("messages", [])
        next_cursor = result.get("nextCursor")

        if messages:
            total_messages += len(messages)
            print(f"  Received {len(messages)} identifier state changes")

            for msg in messages:
                identifier_type = msg.get("type")
                display_value = msg.get("displayValue", msg.get("display_value"))
                confidence = msg.get("confidence")
                print(f"    - {identifier_type}: {display_value} (confidence: {confidence:.3f})")

        # Update cursor for next iteration
        if next_cursor:
            cursor = next_cursor
        else:
            # No new messages, wait a bit
            time.sleep(1)

    print(f"\n  Total messages consumed: {total_messages}")


def trigger_backfill_example(stream_id: str):
    """Trigger backfill for an existing identifier stream."""
    print(f"\n✓ Triggering backfill for stream: {stream_id}")

    result = client.backfill_stream(
        stream_id=stream_id, from_date="2025-01-15T00:00:00Z"  # Backfill from this date
    )

    print(f"  Status: {result.get('status', 'unknown')}")
    if result.get("message"):
        print(f"  Message: {result['message']}")


def recover_stream_example(stream_id: str):
    """Recover/rebuild a stream from publish history."""
    print(f"\n✓ Triggering stream recovery: {stream_id}")

    # Standard checkpoint-based recovery
    result = client.recover_stream(
        stream_id=stream_id,
        ignore_checkpoint=False,  # Use checkpoint
        clear_stream=True,  # Clear and rebuild
    )

    print(f"  Status: {result.get('status', 'unknown')}")
    if result.get("message"):
        print(f"  Message: {result['message']}")


def check_recovery_status():
    """Check recovery status for all streams."""
    print("\n✓ Checking recovery status...")

    status = client.get_recovery_status()
    logs = status.get("logs", [])

    if not logs:
        print("  No recovery operations found")
        return

    print(f"  Found {len(logs)} recovery operations:")
    for log in logs:
        print(f"\n  Stream: {log.get('streamName')}")
        print(f"  Started: {log.get('startedAt')}")
        print(f"  Completed: {log.get('completedAt', 'In Progress')}")
        if log.get("error"):
            print(f"  Error: {log['error']}")
        if log.get("recordsReplayed") is not None:
            print(f"  Records Replayed: {log['recordsReplayed']}")


def get_stream_recovery_info(stream_id: str):
    """Get detailed recovery info for a specific stream."""
    print(f"\n✓ Getting recovery info for stream: {stream_id}")

    info = client.get_stream_recovery_info(stream_id)

    print(f"  Is Rebuilding: {info.get('isRebuilding', False)}")
    print(f"  Last Consumed Journal Entry: {info.get('lastConsumedJournalEntry', 'None')}")
    print(f"  Last Consumed Identifier: {info.get('lastConsumedIdentifier', 'None')}")
    print(f"  Journal Entries to Replay: {info.get('journalEntriesToReplay', 'N/A')}")
    print(f"  Identifiers to Replay: {info.get('identifiersToReplay', 'N/A')}")


def structured_data_example():
    """
    Example: Using Structured Identifier Data

    Demonstrates how to access and use the type-specific structured data
    that comes with each identifier in the stream.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE: Using Structured Identifier Data")
    print("=" * 60)

    # Create a phone-only identifier stream
    stream = client.create_stream(
        name="Phone Numbers with Structured Data",
        data_type="identifier",
        identifier_types=["phone"],
        min_confidence=0.8,
    )

    print(f"\n✓ Created phone identifier stream: {stream.id}")

    # Consume messages and extract structured data
    result = client.consume_stream(stream.id, cursor="0", limit=10)
    messages = result.get("messages", [])

    if messages:
        print(f"\n✓ Processing {len(messages)} phone number messages:")

        for msg in messages:
            details = msg.get("details", {})

            # Extract structured phone data
            country_code = details.get("country_code") or details.get("countryCode")
            area_code = details.get("area_code") or details.get("areaCode")
            is_toll_free = details.get("is_toll_free", details.get("isTollFree", False))
            region = details.get("region")

            print(f"\n  Phone: {msg.get('displayValue')}")
            print(f"    Country: {country_code} ({region or 'unknown'})")
            if area_code:
                print(f"    Area Code: {area_code}")
            print(f"    Toll-Free: {'Yes' if is_toll_free else 'No'}")
            print(f"    Confidence: {msg.get('confidence'):.3f}")

            # Example: Use structured data for routing decisions
            if is_toll_free:
                print(f"    → Action: Add to toll-free scam list")
            elif country_code == "+1" and area_code:
                print(f"    → Action: Block area code {area_code} if threshold met")
            elif country_code != "+1":
                print(f"    → Action: Flag international scam number")
    else:
        print("\n  No messages available yet")

    print("\n" + "=" * 60)
    return stream.id


def comparison_example():
    """
    Comparison: Journal Entry Stream vs Identifier Stream

    This demonstrates the key differences between the two stream types.
    """
    print("\n" + "=" * 60)
    print("COMPARISON: Journal Entry vs Identifier Streams")
    print("=" * 60)

    # Create both types for comparison
    je_stream = client.create_stream(
        name="Phone Call Journal Entries",
        data_type="journal_entry",
        identifier_types=["phone"],
        min_confidence=0.8,
    )
    print(f"\n✓ Journal Entry Stream: {je_stream.id}")
    print(f"  - Publishes: Complete journal entries")
    print(f"  - Frequency: Every matching journal entry")
    print(f"  - Contains: JE details + all linked identifiers + evidence")
    print(f"  - Use case: Track all scam events involving phones")

    id_stream = client.create_stream(
        name="Phone Identifier State Changes",
        data_type="identifier",
        identifier_types=["phone"],
        min_confidence=0.8,
    )
    print(f"\n✓ Identifier Stream: {id_stream.id}")
    print(f"  - Publishes: Identifier state changes")
    print(f"  - Frequency: Only when state changes (confidence, tags, type)")
    print(f"  - Contains: Identifier state + triggering JE reference")
    print(f"  - Use case: Track how specific phone numbers evolve")

    print("\n" + "=" * 60)


# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("Identifier Stream Examples")
    print("=" * 60)

    # Example 1: Create basic identifier stream
    stream_id = create_identifier_stream_basic()

    # Example 2: Create filtered stream
    phone_stream_id = create_identifier_stream_filtered()

    # Example 3: Create stream with backfill
    email_stream_id = create_identifier_stream_with_backfill()

    # Example 4: Consume identifier messages
    consume_identifier_stream(stream_id)

    # Example 5: Continuous consumption (commented out by default)
    # continuous_consumption_example(stream_id, duration_seconds=30)

    # Example 6: Trigger backfill on existing stream
    # trigger_backfill_example(email_stream_id)

    # Example 7: Recover a stream
    # recover_stream_example(stream_id)

    # Example 8: Check recovery status
    # check_recovery_status()

    # Example 9: Get stream recovery info
    # get_stream_recovery_info(stream_id)

    # Example 10: Structured data usage
    # structured_data_example()

    # Example 11: Comparison
    # comparison_example()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
