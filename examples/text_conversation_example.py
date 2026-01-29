#!/usr/bin/env python3
"""
Text Conversation Journal Entry Example

This example demonstrates creating text/messaging conversation journal entries
for various platforms (SMS, WhatsApp, Telegram, Signal, etc.).
"""

import os
from datetime import datetime, timedelta
from scambus_client import ScambusClient, IdentifierLookup, TagLookup

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Create text conversation journal entries."""

    print("=" * 60)
    print("Text Conversation Journal Entry Examples")
    print("=" * 60)

    # Example 1: SMS conversation
    print("\n1. Creating SMS conversation entry...")
    start = datetime(2024, 1, 15, 14, 0)
    entry = client.create_text_conversation(
        description="Suspicious SMS messages requesting immediate payment",
        platform="SMS",
        start_time=start,
        end_time=start + timedelta(minutes=30),
        identifiers=[IdentifierLookup(type="phone", value="+18005551234", confidence=0.9)],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="SMS"),
        ],
    )

    print(f"✓ Created SMS conversation entry: {entry.id}")
    print(f"  Platform: SMS")
    print(f"  Duration: 30 minutes")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 2: WhatsApp conversation
    print("\n2. Creating WhatsApp conversation entry...")
    start = datetime.now()
    entry = client.create_text_conversation(
        description="WhatsApp conversation with suspected cryptocurrency scammer",
        platform="WhatsApp",
        start_time=start,
        end_time=start + timedelta(hours=2),
        identifiers=[IdentifierLookup(type="phone", value="+12125551234", confidence=0.95)],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Crypto"),
        ],
    )

    print(f"✓ Created WhatsApp conversation entry: {entry.id}")
    print(f"  Platform: WhatsApp")
    print(f"  Duration: 2 hours")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 3: Telegram conversation
    print("\n3. Creating Telegram conversation entry...")
    start = datetime(2024, 1, 20, 9, 0)
    entry = client.create_text_conversation(
        description="Telegram conversation regarding fake investment opportunity",
        platform="Telegram",
        start_time=start,
        end_time=start + timedelta(hours=3),
        identifiers=[
            IdentifierLookup(
                type="social_media", value="telegram:@crypto_scammer123", confidence=0.9
            )
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Investment"),
        ],
    )

    print(f"✓ Created Telegram conversation entry: {entry.id}")
    print(f"  Platform: Telegram")
    print(f"  Duration: 3 hours")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 4: Signal conversation
    print("\n4. Creating Signal conversation entry...")
    start = datetime(2024, 1, 22, 16, 30)
    entry = client.create_text_conversation(
        description="Signal conversation with romance scammer",
        platform="Signal",
        start_time=start,
        end_time=start + timedelta(hours=1, minutes=15),
        identifiers=[IdentifierLookup(type="phone", value="+447123456789", confidence=0.85)],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Romance"),
        ],
    )

    print(f"✓ Created Signal conversation entry: {entry.id}")
    print(f"  Platform: Signal")
    print(f"  Duration: 1 hour 15 minutes")
    print(f"  Identifiers: {len(entry.identifiers)}")

    print("\n✓ All text conversation entries created successfully!")

    # Example with media
    print("\n5. Example with screenshot evidence...")
    print("Note: This requires actual image files. Example code:")
    print(
        """
    # Upload conversation screenshots
    screenshot1 = client.upload_media("chat-screenshot-1.png")
    screenshot2 = client.upload_media("chat-screenshot-2.png")

    # Create conversation entry with screenshots
    start = datetime.now()
    entry = client.create_text_conversation(
        description="WhatsApp scam conversation with screenshots",
        platform="WhatsApp",
        start_time=start,
        end_time=start + timedelta(hours=1),
        media=[screenshot1, screenshot2],  # Automatically creates evidence
        identifiers=[
            IdentifierLookup(type="phone", value="+12125551234", confidence=0.95)
        ],
    )
    """
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
