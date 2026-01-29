#!/usr/bin/env python3
"""
One-off script to verify is_test filtering on export streams.

This script:
1. Creates a temporary export stream filtering for phone numbers with is_test=True
2. Listens in the background
3. Creates two journal entries (one matching, one not)
4. Verifies only the matching entry arrives

Run with: python scripts/test_is_test_stream_filtering.py
"""

import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List

from scambus_client import ScambusClient


def poll_stream_for_events(
    client: ScambusClient,
    stream_id: str,
    expected_count: int,
    timeout_seconds: float = 30.0,
    poll_interval: float = 1.0,
) -> List[Dict[str, Any]]:
    """Poll a stream until we receive the expected number of events or timeout."""
    all_events = []
    cursor = "0"
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            result = client.consume_stream(
                stream_id=stream_id,
                cursor=cursor,
                order="asc",
                limit=100,
                timeout=5.0,
            )

            events = result.get("events", []) or result.get("messages", [])
            if events:
                all_events.extend(events)
                cursor = result.get("cursor") or result.get("nextCursor")

            if len(all_events) >= expected_count:
                break

        except Exception as e:
            print(f"Error polling stream: {e}")

        time.sleep(poll_interval)

    return all_events


def main():
    """Main test function."""
    print("=" * 60)
    print("Test: is_test filtering on export streams")
    print("=" * 60)

    # Create client using built-in credential discovery
    print("\n1. Creating client...")
    client = ScambusClient()
    print(f"   Connected to: {client.api_url}")

    # Generate unique test identifiers
    test_run_id = str(uuid.uuid4())[:8]
    test_phone = f"+1555{test_run_id.replace('-', '')[:7]}"
    non_test_phone = f"+1666{test_run_id.replace('-', '')[:7]}"

    stream = None
    test_entry_id = None
    non_test_entry_id = None

    try:
        # Create temporary stream filtering for is_test=True
        print("\n2. Creating temporary export stream...")
        print("   Filter: journal entries with is_test=True")

        filter_expr = "$.is_test == true"

        stream = client.create_temporary_stream(
            data_type="journal_entry",
            identifier_types="phone",
            filter_expression=filter_expr,
            name=f"is-test-filter-test-{test_run_id}",
        )
        print(f"   Stream created: {stream.id}")
        print(f"   Filter expression: {stream.filter_expression}")

        # Give the stream a moment to be ready
        time.sleep(2)

        # Start polling in background thread
        print("\n3. Starting background stream listener...")
        with ThreadPoolExecutor(max_workers=1) as executor:
            poll_future = executor.submit(
                poll_stream_for_events,
                client,
                stream.id,
                expected_count=1,
                timeout_seconds=30.0,
                poll_interval=1.0,
            )

            time.sleep(1)

            # Create test journal entry (is_test=True) - SHOULD match
            print("\n4. Creating journal entries...")
            print(f"   Creating TEST entry with phone: {test_phone} (is_test=True)")
            test_entry = client.create_journal_entry(
                entry_type="phone_call",
                description=f"Test entry for stream filter test {test_run_id}",
                details={"direction": "inbound", "platform": "pstn"},
                identifier_lookups=[{"type": "phone", "value": test_phone, "confidence": 0.9}],
                is_test=True,
            )
            test_entry_id = test_entry.id
            print(f"   Test entry created: {test_entry_id}")
            print(f"   Entry is_test flag: {test_entry.is_test}")

            # Create non-test journal entry (is_test=False) - should NOT match
            print(f"\n   Creating NON-TEST entry with phone: {non_test_phone} (is_test=False)")
            non_test_entry = client.create_journal_entry(
                entry_type="phone_call",
                description=f"Non-test entry for stream filter test {test_run_id}",
                details={"direction": "outbound", "platform": "pstn"},
                identifier_lookups=[{"type": "phone", "value": non_test_phone, "confidence": 0.9}],
                is_test=False,
            )
            non_test_entry_id = non_test_entry.id
            print(f"   Non-test entry created: {non_test_entry_id}")
            print(f"   Entry is_test flag: {non_test_entry.is_test}")

            # Wait for polling to complete
            print("\n5. Waiting for stream events...")
            try:
                events = poll_future.result(timeout=35.0)
            except FuturesTimeoutError:
                events = []
                print("   WARNING: Polling timed out")

        # Analyze results
        print("\n6. Analyzing results...")
        print(f"   Total events received: {len(events)}")

        received_entry_ids = set()
        for event in events:
            event_id = event.get("id") or event.get("journal_entry_id")
            if event_id:
                received_entry_ids.add(event_id)
            print(f"   - Event: {event_id}")
            if "is_test" in event:
                print(f"     is_test: {event.get('is_test')}")

        # Verify results
        print("\n7. Verification...")
        success = True

        if test_entry_id in received_entry_ids:
            print(f"   [PASS] Test entry ({test_entry_id}) was received")
        else:
            print(f"   [FAIL] Test entry ({test_entry_id}) was NOT received")
            success = False

        if non_test_entry_id not in received_entry_ids:
            print(f"   [PASS] Non-test entry ({non_test_entry_id}) was correctly excluded")
        else:
            print(f"   [FAIL] Non-test entry ({non_test_entry_id}) was incorrectly included")
            success = False

        if len(events) == 1:
            print("   [PASS] Received exactly 1 event")
        else:
            print(f"   [WARN] Received {len(events)} events, expected 1")
            if len(events) == 0:
                print("     Note: Zero events might indicate stream timing issue")

        print("\n" + "=" * 60)
        if success:
            print("TEST PASSED: is_test filtering works correctly!")
        else:
            print("TEST FAILED: is_test filtering did not work as expected")
        print("=" * 60)

        return success

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n8. Cleanup...")
        try:
            if stream:
                client.delete_stream(stream.id)
                print(f"   Deleted stream: {stream.id}")
        except Exception as e:
            print(f"   Warning: Could not delete stream: {e}")

        try:
            if test_entry_id:
                client.delete_journal_entry(test_entry_id)
                print(f"   Deleted test entry: {test_entry_id}")
        except Exception as e:
            print(f"   Warning: Could not delete test entry: {e}")

        try:
            if non_test_entry_id:
                client.delete_journal_entry(non_test_entry_id)
                print(f"   Deleted non-test entry: {non_test_entry_id}")
        except Exception as e:
            print(f"   Warning: Could not delete non-test entry: {e}")


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
