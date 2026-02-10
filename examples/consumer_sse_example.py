"""
Example: Consuming a Scambus Export Stream via SSE (Server-Sent Events)

SSE provides real-time streaming with lower latency than polling. The
server keeps a persistent HTTP connection open and pushes messages to
your client as they arrive.

This is the recommended method for real-time consumption.

Prerequisites:
    pip install git+https://github.com/scambus/python-client.git
    pip install sseclient-py requests

You will need:
    - An API key ID and secret (provided by your Scambus administrator)
    - A consumer key (UUID identifying the stream to read from)

SSE Event Types:
    - connected  : Sent immediately on connection. Contains stream metadata.
    - batch      : Array of messages during initial historical replay.
    - message    : Individual real-time message after replay is complete.
    - error      : Error notification.
    - : heartbeat: Keepalive comment sent every ~15 seconds (handled by SSE client).
"""

import json
import os
import time

import requests
import sseclient

# --- Configuration ---
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


def basic_sse_example():
    """
    Connect to the SSE endpoint and print messages as they arrive.
    """
    url = f"{API_URL}/consume/{CONSUMER_KEY}/stream"
    headers = {
        "X-API-Key": f"{API_KEY_ID}:{API_KEY_SECRET}",
        "Accept": "text/event-stream",
    }
    params = {
        "cursor": "$",             # "$" = new messages only; "0" = from beginning
        "include_test": "false",
    }

    print(f"Connecting to SSE stream: {CONSUMER_KEY}")
    print("Waiting for messages... (Ctrl+C to stop)\n")

    response = requests.get(url, headers=headers, params=params, stream=True)
    response.raise_for_status()

    client = sseclient.SSEClient(response)

    for event in client.events():
        try:
            if event.event == "connected":
                info = json.loads(event.data)
                print(f"Connected to stream: {info.get('stream', CONSUMER_KEY)}")

            elif event.event == "batch":
                # Initial historical replay — array of messages
                messages = json.loads(event.data)
                print(f"Received batch of {len(messages)} messages")
                for msg in messages:
                    process_message(msg)

            elif event.event == "message":
                # Real-time individual message
                msg = json.loads(event.data)
                process_message(msg)

            elif event.event == "error":
                error = json.loads(event.data)
                print(f"Error: {error.get('error', event.data)}")
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse event ({event.event}): {e}")


def sse_with_reconnection():
    """
    SSE consumption with automatic reconnection.

    If the connection drops, reconnect using the last cursor received.
    This ensures you resume without gaps or duplicates.
    """
    url = f"{API_URL}/consume/{CONSUMER_KEY}/stream"
    headers = {
        "X-API-Key": f"{API_KEY_ID}:{API_KEY_SECRET}",
        "Accept": "text/event-stream",
    }

    # Track the last cursor received so we can resume on reconnect
    last_cursor = "$"
    reconnect_delay = 1.0
    max_reconnect_delay = 60.0

    print(f"Connecting to SSE stream with auto-reconnection: {CONSUMER_KEY}")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            params = {
                "cursor": last_cursor,
                "include_test": "false",
            }

            response = requests.get(url, headers=headers, params=params, stream=True)
            response.raise_for_status()

            client = sseclient.SSEClient(response)
            reconnect_delay = 1.0  # Reset backoff on successful connection

            for event in client.events():
                try:
                    if event.event == "connected":
                        info = json.loads(event.data)
                        print(f"Connected to stream: {info.get('stream', CONSUMER_KEY)}")

                    elif event.event == "batch":
                        messages = json.loads(event.data)
                        for msg in messages:
                            process_message(msg)
                            # Save cursor from each message for resume
                            if msg.get("cursor"):
                                last_cursor = msg["cursor"]

                    elif event.event == "message":
                        msg = json.loads(event.data)
                        process_message(msg)
                        # Save cursor for resume
                        if msg.get("cursor"):
                            last_cursor = msg["cursor"]

                    elif event.event == "error":
                        error = json.loads(event.data)
                        print(f"Stream error: {error.get('error', event.data)}")
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse event ({event.event}): {e}")

        except KeyboardInterrupt:
            print(f"\nDisconnected. Last cursor: {last_cursor}")
            break

        except requests.exceptions.ConnectionError:
            print(f"Connection lost. Reconnecting in {reconnect_delay:.0f}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            if status == 429:
                print("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
            elif status == 503:
                print("Stream rebuilding. Retrying in 10 seconds...")
                time.sleep(10)
            else:
                print(f"HTTP error: {e}")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

        except Exception as e:
            print(f"Unexpected error: {e}. Reconnecting in {reconnect_delay:.0f}s...")
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def process_message(msg: dict):
    """Process a single stream message (identifier or journal entry)."""
    if "identifier_id" in msg:
        # Identifier stream message
        print(
            f"  [{msg.get('cursor', '')}] Identifier: "
            f"{msg.get('type', 'unknown')} = {msg.get('display_value', 'N/A')} "
            f"(confidence: {msg.get('confidence', 'N/A')})"
        )
    else:
        # Journal entry stream message
        print(
            f"  [{msg.get('cursor', '')}] "
            f"Journal Entry: {msg.get('type', 'unknown')} — {msg.get('description', '')[:80]}"
        )


if __name__ == "__main__":
    print("=== SSE Consumer Example ===\n")

    # Uncomment the example you want to run:

    # Simple connection (no reconnection logic):
    # basic_sse_example()

    # Production-ready with auto-reconnection:
    sse_with_reconnection()
