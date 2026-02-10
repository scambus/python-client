"""
End-to-end integration test for the export stream pipeline.

Verifies the full flow: create stream -> connect SSE -> create data -> receive in real-time.

Exercises: create_stream(), get_stream_info(), consume_stream(), SSE consumption, delete_stream()

Requirements:
    - Running Scambus backend at http://localhost:8080/api (or configured URL)
    - API key credentials (SCAMBUS_API_KEY_ID + SCAMBUS_API_KEY_SECRET)
    - pip install sseclient-py

Run:
    SCAMBUS_API_KEY_ID="<key-id>" SCAMBUS_API_KEY_SECRET="<secret>" \\
        python tests/integration/test_stream_e2e.py

    Or set SCAMBUS_API_URL to override the API base URL (default: http://localhost:8080/api).
"""

import json
import os
import sys
import threading
import time
import uuid

import requests
import sseclient

from scambus_client import ScambusClient, IdentifierLookup


def main():
    # --- Setup ---
    api_url = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
    api_key_id = os.getenv("SCAMBUS_API_KEY_ID")
    api_key_secret = os.getenv("SCAMBUS_API_KEY_SECRET")

    if not api_key_id or not api_key_secret:
        print("ERROR: SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET env vars required.")
        print("  Create an API key in the Automations UI.")
        sys.exit(1)

    test_id = uuid.uuid4().hex[:8]
    test_email = f"e2e-test-{test_id}@scambus-test.example"
    stream_name = f"E2E Test {test_id}"

    print("=== Stream E2E Integration Test ===")
    print(f"Test ID:    {test_id}")
    print(f"Test email: {test_email}")
    print(f"API URL:    {api_url}")
    print()

    client = ScambusClient(
        api_url=api_url,
        api_key_id=api_key_id,
        api_key_secret=api_key_secret,
    )
    api_key_header = f"{api_key_id}:{api_key_secret}"

    stream = None
    try:
        # --- Step 1: Create stream ---
        print("[1/7] Creating export stream...")
        stream = client.create_stream(
            name=stream_name,
            data_type="journal_entry",
            filter_criteria={"types": ["detection"]},
        )
        print(f"  Stream ID:     {stream.id}")
        print(f"  Consumer key:  {stream.consumer_key}")
        assert stream.consumer_key, "Stream consumer_key is missing"
        assert stream.data_type == "journal_entry"
        print("  OK")
        print()

        consumer_key = stream.consumer_key

        # --- Step 2: Verify stream info ---
        print("[2/7] Verifying stream info...")
        info = client.get_stream_info(consumer_key)
        print(f"  Name:      {info.get('name')}")
        print(f"  Data type: {info.get('dataType', info.get('data_type'))}")
        assert info.get("name") == stream_name, f"Name mismatch: {info.get('name')}"
        print("  OK")
        print()

        # --- Step 3: Start SSE listener in background thread ---
        print("[3/7] Starting SSE listener...")
        sse_messages = []
        sse_connected = threading.Event()
        sse_error = []

        def sse_listener():
            try:
                url = f"{api_url}/consume/{consumer_key}/stream"
                headers = {
                    "X-API-Key": api_key_header,
                    "Accept": "text/event-stream",
                }
                params = {"cursor": "$", "include_test": "true"}

                resp = requests.get(url, headers=headers, params=params, stream=True, timeout=60)
                resp.raise_for_status()

                sse_client = sseclient.SSEClient(resp)
                for event in sse_client.events():
                    if event.event == "connected":
                        sse_connected.set()
                    elif event.event == "message":
                        try:
                            msg = json.loads(event.data)
                            sse_messages.append(msg)
                        except json.JSONDecodeError:
                            pass
                    elif event.event == "batch":
                        try:
                            msgs = json.loads(event.data)
                            sse_messages.extend(msgs)
                        except json.JSONDecodeError:
                            pass
                    elif event.event == "error":
                        sse_error.append(event.data)
            except Exception as e:
                sse_error.append(str(e))
                sse_connected.set()  # unblock main thread on error

        thread = threading.Thread(target=sse_listener, daemon=True)
        thread.start()

        # Wait for SSE to connect
        if not sse_connected.wait(timeout=10):
            print("  WARNING: SSE connected event not received within 10s, proceeding anyway...")
        else:
            if sse_error:
                print(f"  ERROR: SSE connection failed: {sse_error[0]}")
                sys.exit(1)
            print("  SSE connected")
        print()

        # --- Step 4: Short delay to ensure SSE is blocking on XREAD ---
        print("[4/7] Waiting for SSE to be ready...")
        time.sleep(1)
        print("  OK")
        print()

        # --- Step 5: Create detection to trigger stream publishing ---
        print("[5/7] Creating detection...")
        entry = client.create_detection(
            description=f"E2E test detection {test_id}",
            identifiers=[
                IdentifierLookup(
                    type="email",
                    value=test_email,
                    confidence=0.95,
                )
            ],
            is_test=True,
        )
        print(f"  Journal entry ID: {entry.id}")
        print(f"  Type:             {entry.type}")
        print("  OK")
        print()

        # --- Step 6: Wait for SSE message ---
        print("[6/7] Waiting for SSE message (up to 15s)...")
        deadline = time.time() + 15
        while time.time() < deadline:
            if sse_messages:
                # Wait a bit more to collect additional messages
                time.sleep(2)
                break
            time.sleep(0.25)

        if sse_error:
            print(f"  SSE error: {sse_error}")

        if not sse_messages:
            print("  FAIL: No SSE messages received within 15 seconds")
            sys.exit(1)

        print(f"  Received {len(sse_messages)} SSE message(s)")
        msg = sse_messages[0]
        print(f"  Message type: {msg.get('type')}")
        print(f"  Description:  {msg.get('description', '')[:80]}")

        # Verify the message matches what we created
        assert msg.get("type") == "detection", f"Expected type 'detection', got '{msg.get('type')}'"
        assert test_id in msg.get("description", ""), "Description doesn't contain test ID"
        print("  SSE assertion OK")
        print()

        # --- Step 7: Verify via HTTP polling ---
        print("[7/7] Verifying via HTTP polling...")
        poll_result = client.consume_stream(
            consumer_key,
            cursor="0",
            include_test=True,
        )
        poll_messages = poll_result.get("messages", [])
        print(f"  Poll returned {len(poll_messages)} message(s)")

        # Find our message in the poll results
        found = False
        for pm in poll_messages:
            if test_id in pm.get("description", ""):
                found = True
                break

        if not found:
            print("  FAIL: Detection not found in poll results")
            sys.exit(1)

        print("  Poll assertion OK")
        print()

        print("=== ALL TESTS PASSED ===")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # --- Cleanup ---
        if stream:
            print(f"\nCleaning up: deleting stream {stream.id}...")
            try:
                client.delete_stream(stream.id)
                print("  Stream deleted")
            except Exception as e:
                print(f"  WARNING: Failed to delete stream: {e}")


if __name__ == "__main__":
    main()
