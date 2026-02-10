"""
Example: Consuming a Scambus Export Stream via HTTP Polling

This is the recommended example for external consumers who have been
given a consumer key and API key credentials. It demonstrates:

- Authenticating with API key ID + secret
- Fetching stream metadata before consuming
- Continuous polling with cursor-based pagination
- Handling all cursor values (beginning, end, resume)
- Error handling for stream-specific HTTP status codes
- Processing both identifier and journal entry messages

Prerequisites:
    pip install git+https://github.com/scambus/python-client.git

You will need:
    - An API key ID and secret (provided by your Scambus administrator)
    - A consumer key (UUID identifying the stream to read from)
"""

import os
import time

from scambus_client import ScambusClient, ScambusAPIError

# --- Configuration ---
# Set these via environment variables or replace with your values.
API_URL = os.getenv("SCAMBUS_API_URL", "https://scambus.net/api")
API_KEY_ID = os.getenv("SCAMBUS_API_KEY_ID")
API_KEY_SECRET = os.getenv("SCAMBUS_API_KEY_SECRET")
CONSUMER_KEY = os.getenv("SCAMBUS_CONSUMER_KEY")

if not API_KEY_ID or not API_KEY_SECRET:
    print("Error: Set SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET")
    exit(1)
if not CONSUMER_KEY:
    print("Error: Set SCAMBUS_CONSUMER_KEY")
    exit(1)


def basic_poll_example():
    """Fetch a single batch of messages from the stream."""
    client = ScambusClient(
        api_url=API_URL,
        api_key_id=API_KEY_ID,
        api_key_secret=API_KEY_SECRET,
    )

    # Fetch the first batch of messages (oldest first)
    result = client.consume_stream(
        CONSUMER_KEY,
        cursor="0",     # Start from the beginning
        order="asc",    # Oldest first
        limit=100,
    )

    for msg in result["messages"]:
        print(msg)

    # The response includes a cursor to fetch the next batch
    print(f"Next cursor: {result['next_cursor']}")
    print(f"Has more: {result['has_more']}")


def stream_info_example():
    """Check stream metadata before consuming."""
    client = ScambusClient(
        api_url=API_URL,
        api_key_id=API_KEY_ID,
        api_key_secret=API_KEY_SECRET,
    )

    info = client.get_stream_info(CONSUMER_KEY)
    print(f"Stream: {info.get('name')}")
    print(f"Data type: {info.get('data_type')}")
    print(f"Messages in stream: {info.get('messages_in_stream')}")

    cursors = info.get("cursors", {})
    print(f"Recommended cursor: {cursors.get('recommended')}")
    print(f"First entry: {info.get('first_entry')}")
    print(f"Last entry: {info.get('last_entry')}")

    return info


def continuous_polling_example():
    """
    Continuously poll for messages, processing each batch and advancing
    the cursor. This is the standard pattern for consuming a stream.
    """
    client = ScambusClient(
        api_url=API_URL,
        api_key_id=API_KEY_ID,
        api_key_secret=API_KEY_SECRET,
    )

    # Start from the beginning. To receive only new messages, use cursor="$".
    # To resume, load cursor from your persistent storage (file, database, etc.).
    cursor = "0"

    print(f"Starting continuous poll from cursor: {cursor}")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            try:
                result = client.consume_stream(
                    CONSUMER_KEY,
                    cursor=cursor,
                    order="asc",
                    limit=100,
                )
            except ScambusAPIError as e:
                status = getattr(e, "status_code", None)

                if status == 410:
                    # Cursor outside retention window — reset
                    print("Cursor expired (outside retention window). Resetting to beginning.")
                    cursor = "0"
                    continue
                elif status == 416:
                    # Cursor before stream start — data was trimmed
                    print("Cursor before stream start (data trimmed). Resetting to beginning.")
                    cursor = "0"
                    continue
                elif status == 429:
                    # Rate limited — back off
                    print("Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                elif status == 503:
                    # Stream rebuilding — retry shortly
                    print("Stream is being rebuilt. Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                else:
                    raise

            messages = result["messages"]
            for msg in messages:
                process_message(msg)

            # Advance the cursor
            if result["next_cursor"]:
                cursor = result["next_cursor"]

            # If there are no more messages, wait before polling again
            if not result["has_more"]:
                time.sleep(5)

    except KeyboardInterrupt:
        print(f"\nStopped. Last cursor: {cursor}")
        print("Save this cursor to resume later.")


def process_message(msg: dict):
    """
    Process a single stream message.

    For identifier streams, messages contain:
        identifier_id, type, display_value, confidence, tags,
        triggering_journal_entry, etc.

    For journal entry streams, messages contain:
        id, type, description, performed_at, identifiers,
        evidence, originator, etc.
    """
    # Detect message type
    if "identifier_id" in msg:
        # Identifier stream message
        print(
            f"  Identifier: {msg.get('type', 'unknown')} = {msg.get('display_value', 'N/A')} "
            f"(confidence: {msg.get('confidence', 'N/A')})"
        )

        # Access tags
        for tag in msg.get("tags", []):
            print(f"    Tag: {tag.get('tag_title')}: {tag.get('value')}")

        # Access triggering journal entry
        tje = msg.get("triggering_journal_entry")
        if tje:
            print(f"    Triggered by: {tje.get('type', 'unknown')} at {tje.get('performed_at', 'N/A')}")

    else:
        # Journal entry stream message
        print(
            f"  Journal Entry: {msg.get('type', 'unknown')} — {msg.get('description', '')[:80]}"
        )

        # Access linked identifiers
        for ident in msg.get("identifiers", []):
            print(f"    Identifier: {ident.get('type', 'unknown')} = {ident.get('display_value', 'N/A')}")


# --- Cursor values reference ---
#
# | Cursor               | Meaning                                              |
# |----------------------|------------------------------------------------------|
# | "0"                  | Read from the beginning of the stream                |
# | "$"                  | Read only new messages arriving after this point     |
# | "1735689600000-0"    | Resume from a specific message ID (from msg cursor)  |


if __name__ == "__main__":
    print("=== Stream Info ===\n")
    stream_info_example()

    print("\n=== Basic Poll ===\n")
    basic_poll_example()

    print("\n=== Continuous Polling ===\n")
    continuous_polling_example()
