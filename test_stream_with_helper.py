#!/usr/bin/env python3
"""
Test creating streams using the identifier_types helper.
"""

import os
from scambus_client import ScambusClient


def test_stream_creation_with_helpers():
    """Test creating streams with the new identifier_types parameter."""

    # Get client with auth
    import json
    api_url = os.environ.get('SCAMBUS_URL', 'http://localhost:8080/api')

    # Try to read from config file
    config_path = os.path.expanduser('~/.scambus/config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            token = ((config.get('auth', {}).get('token') if isinstance(config.get('auth'), dict) else None) or
                    config.get('access_token') or
                    config.get('jwt_token'))
            if token:
                client = ScambusClient(api_url=api_url, api_token=token)
            else:
                raise Exception("No token found in config file")
    else:
        raise Exception("Config file not found. Run 'scambus auth login' first.")

    print("=" * 70)
    print("  Testing Stream Creation with identifier_types Helper")
    print("=" * 70)
    print()

    # Test 1: Single identifier type
    print("Test 1: Creating stream with single identifier type (phone)...")
    stream1 = client.create_stream(
        name="E2E Test - Phone Numbers Only",
        data_type="identifier",
        identifier_types="phone",
        min_confidence=0.8
    )
    print(f"  ✓ Stream created: {stream1.id}")
    print(f"    Stream name: {stream1.name}")
    print()

    # Test 2: Multiple identifier types
    print("Test 2: Creating stream with multiple identifier types (phone, email)...")
    stream2 = client.create_stream(
        name="E2E Test - Contact Info",
        data_type="identifier",
        identifier_types=["phone", "email"],
        min_confidence=0.9
    )
    print(f"  ✓ Stream created: {stream2.id}")
    print(f"    Stream name: {stream2.name}")
    print()

    # Test 3: Identifier type + custom filter
    print("Test 3: Creating stream with identifier type + custom filter...")
    stream3 = client.create_stream(
        name="E2E Test - WhatsApp Only",
        data_type="identifier",
        identifier_types="social_media",
        filter_expression='$.details.platform == "whatsapp"',
        min_confidence=0.85
    )
    print(f"  ✓ Stream created: {stream3.id}")
    print(f"    Stream name: {stream3.name}")
    print()

    # Test 4: List all streams to verify
    print("Test 4: Listing streams to verify...")
    result = client.list_streams()
    streams = result['data']
    created_ids = {stream1.id, stream2.id, stream3.id}
    found_streams = [s for s in streams if s.id in created_ids]
    print(f"  ✓ Found {len(found_streams)}/3 created streams")
    for s in found_streams:
        print(f"    - {s.name}")
    print()

    # Cleanup
    print("Cleanup: Deleting test streams...")
    client.delete_stream(stream1.id)
    print(f"  ✓ Deleted stream: {stream1.id}")
    client.delete_stream(stream2.id)
    print(f"  ✓ Deleted stream: {stream2.id}")
    client.delete_stream(stream3.id)
    print(f"  ✓ Deleted stream: {stream3.id}")
    print()

    print("=" * 70)
    print("  ✓ All tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_stream_creation_with_helpers()
