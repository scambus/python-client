#!/usr/bin/env python3
"""
Phone Call Journal Entry Example

This example demonstrates creating phone call journal entries with
typed classes for identifiers and tags.
"""

import os
from datetime import datetime, timedelta, timezone
from scambus_client import ScambusClient, IdentifierLookup, TagLookup

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Create phone call journal entries using typed classes."""

    print("=" * 60)
    print("Phone Call Journal Entry Examples")
    print("=" * 60)

    # Example 1: Outbound call (no answer)
    print("\n1. Creating outbound call entry...")
    now = datetime.now(timezone.utc)
    entry = client.create_phone_call(
        description="Called suspect regarding fraudulent transaction - no answer",
        direction="outbound",
        start_time=now,
        end_time=now + timedelta(minutes=1),
        identifiers=[IdentifierLookup(type="phone", value="+12125551234", confidence=1.0)],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Financial"),
        ],
    )

    print(f"Created phone call entry: {entry.id}")
    print(f"  Direction: outbound")
    print(f"  Duration: 1 minute")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 2: Inbound call with recording
    print("\n2. Creating inbound call entry with recording...")
    entry = client.create_phone_call(
        description="Received suspicious call claiming to be IRS demanding payment",
        direction="inbound",
        start_time=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 15, 10, 35, tzinfo=timezone.utc),
        recording_url="https://storage.example.com/recordings/irs-scam-call.mp3",
        identifiers=[
            IdentifierLookup(type="phone", value="+18005559999", confidence=0.9, label="caller")
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="IRS"),
            TagLookup(tag_name="HighPriority"),
        ],
    )

    print(f"Created phone call entry: {entry.id}")
    print(f"  Direction: inbound")
    print(f"  Duration: 5 minutes")
    print(f"  Recording: Available")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 3: Call with transcript
    print("\n3. Creating call entry with transcript URL...")
    start = datetime(2024, 1, 20, 14, 15, tzinfo=timezone.utc)
    entry = client.create_phone_call(
        description="Call with suspected tech support scammer",
        direction="outbound",
        start_time=start,
        end_time=start + timedelta(minutes=12),
        recording_url="https://storage.example.com/recordings/tech-scam.mp3",
        transcript_url="https://storage.example.com/transcripts/tech-scam.txt",
        identifiers=[IdentifierLookup(type="phone", value="+18005551234", confidence=0.95)],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="TechSupport"),
            TagLookup(tag_name="EvidenceCollected"),
        ],
    )

    print(f"Created phone call entry: {entry.id}")
    print(f"  Direction: outbound")
    print(f"  Duration: 12 minutes")
    print(f"  Recording: Available")
    print(f"  Transcript: Available")
    print(f"  Identifiers: {len(entry.identifiers)}")

    print("\nAll phone call entries created successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        raise
