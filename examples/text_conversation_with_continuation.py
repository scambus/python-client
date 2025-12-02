#!/usr/bin/env python3
"""
Text Conversation with Continuation Example

This example demonstrates the parent-child structure for text conversations:
1. Create a parent `text_conversation` entry with metadata
2. Add messages via `conversation_continuation` child entries
3. Handle non-contiguous messages (time gaps)
4. Mark identifier positions within message text

This structure allows adding messages incrementally and tracking
conversation history over time.
"""

import os
from datetime import datetime
from scambus_client import ScambusClient
from scambus_client.models import (
    TextConversationDetails,
    ConversationContinuationDetails,
    ConversationMessage,
    MessageIdentifierRef,
)

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate text conversation with continuation entries."""

    print("=" * 70)
    print("Text Conversation with Continuation Example")
    print("=" * 70)

    # =========================================================================
    # STEP 1: Create the parent conversation
    # =========================================================================
    print("\n1. Creating parent text_conversation entry...")

    parent = client.create_journal_entry(
        entry_type="text_conversation",
        description="WhatsApp scam conversation - tech support fraud",
        details=TextConversationDetails(
            platform="whatsapp",
            conversation_type="individual",
            source_type="export",
            export_format="json",
        ).to_dict(),
        # Define identifiers for all participants
        # The 'ref' field is used to reference these in messages via sender_ref
        identifier_lookups=[
            {
                "type": "phone",
                "value": "+1555123456",
                "ref": "scammer",
                "confidence": 0.9,
            },
            {
                "type": "phone",
                "value": "+1555987654",
                "ref": "victim",
                "confidence": 1.0,
            },
        ],
    )

    print(f"✓ Created parent conversation: {parent.id}")
    print(f"  Type: {parent.type}")
    print(f"  Platform: {parent.details.get('platform')}")

    # =========================================================================
    # STEP 2: Add initial batch of messages (contiguous)
    # =========================================================================
    print("\n2. Adding initial messages as conversation_continuation...")

    initial_messages = [
        ConversationMessage(
            index=0,
            message_id="msg_001",
            timestamp=datetime(2025, 1, 15, 10, 0, 0),
            body="Hello, this is Microsoft Support. Your computer has a virus.",
            is_outgoing=False,
            sender_ref="scammer",  # References identifier_lookup with ref="scammer"
        ),
        ConversationMessage(
            index=1,
            message_id="msg_002",
            timestamp=datetime(2025, 1, 15, 10, 1, 30),
            body="Oh no! What should I do?",
            is_outgoing=True,
            sender_ref="victim",
        ),
        ConversationMessage(
            index=2,
            message_id="msg_003",
            timestamp=datetime(2025, 1, 15, 10, 2, 15),
            body="Please download TeamViewer and give me the access code.",
            is_outgoing=False,
            sender_ref="scammer",
        ),
    ]

    continuation1 = client.create_journal_entry(
        entry_type="conversation_continuation",
        description="Initial messages",
        details=ConversationContinuationDetails(
            messages=initial_messages,
            reason="initial import",
        ).to_dict(),
        parent_journal_entry_id=parent.id,  # Link to parent conversation
        identifier_lookups=[
            {"type": "phone", "value": "+1555123456", "ref": "scammer"},
            {"type": "phone", "value": "+1555987654", "ref": "victim"},
        ],
    )

    print(f"✓ Added {len(initial_messages)} initial messages: {continuation1.id}")

    # =========================================================================
    # STEP 3: Add later messages (non-contiguous - time gap)
    # =========================================================================
    print("\n3. Adding later messages (non-contiguous)...")

    # These messages happen hours later - use non_contiguous=True
    # to show a visual separator in the UI
    later_messages = [
        ConversationMessage(
            index=3,  # Continue from where we left off
            message_id="msg_004",
            timestamp=datetime(2025, 1, 15, 14, 30, 0),  # 4+ hours later
            body="I gave you access. Now what?",
            is_outgoing=True,
            sender_ref="victim",
        ),
        ConversationMessage(
            index=4,
            message_id="msg_005",
            timestamp=datetime(2025, 1, 15, 14, 31, 0),
            body="Please send $500 in gift cards to fix your computer.",
            is_outgoing=False,
            sender_ref="scammer",
        ),
    ]

    continuation2 = client.create_journal_entry(
        entry_type="conversation_continuation",
        description="Later messages after time gap",
        details=ConversationContinuationDetails(
            messages=later_messages,
            reason="additional messages",
            non_contiguous=True,  # Shows visual separator in UI
        ).to_dict(),
        parent_journal_entry_id=parent.id,
        identifier_lookups=[
            {"type": "phone", "value": "+1555123456", "ref": "scammer"},
            {"type": "phone", "value": "+1555987654", "ref": "victim"},
        ],
    )

    print(f"✓ Added {len(later_messages)} later messages: {continuation2.id}")
    print("  (marked as non_contiguous due to time gap)")

    # =========================================================================
    # STEP 4: Messages with detected identifiers
    # =========================================================================
    print("\n4. Adding message with identifier references...")

    # When messages contain identifiers (phone numbers, emails, URLs),
    # use identifier_refs to mark their positions for clickable links in the UI
    message_body = "Send the gift cards to this number: +1555999888. Or pay at https://scam-payment.example.com/pay"

    # Calculate byte positions for identifiers
    phone_in_msg = "+1555999888"
    url_in_msg = "https://scam-payment.example.com/pay"

    phone_position = message_body.encode("utf-8").find(phone_in_msg.encode("utf-8"))
    phone_length = len(phone_in_msg.encode("utf-8"))

    url_position = message_body.encode("utf-8").find(url_in_msg.encode("utf-8"))
    url_length = len(url_in_msg.encode("utf-8"))

    messages_with_identifiers = [
        ConversationMessage(
            index=5,
            message_id="msg_006",
            timestamp=datetime(2025, 1, 15, 14, 35, 0),
            body=message_body,
            is_outgoing=False,
            sender_ref="scammer",
            # Mark identifier positions in the message body
            identifier_refs=[
                MessageIdentifierRef(
                    ref="payment_phone",  # Local reference name
                    field="body",
                    position=phone_position,  # Byte offset
                    length=phone_length,  # Byte length
                ),
                MessageIdentifierRef(
                    ref="payment_url",
                    field="body",
                    position=url_position,
                    length=url_length,
                ),
            ],
        ),
    ]

    continuation3 = client.create_journal_entry(
        entry_type="conversation_continuation",
        description="Payment instructions from scammer",
        details=ConversationContinuationDetails(
            messages=messages_with_identifiers,
            reason="payment request",
            non_contiguous=True,
        ).to_dict(),
        parent_journal_entry_id=parent.id,
        identifier_lookups=[
            {"type": "phone", "value": "+1555123456", "ref": "scammer"},
            {"type": "phone", "value": "+1555987654", "ref": "victim"},
            # New identifiers discovered in this message
            {
                "type": "phone",
                "value": "+1555999888",
                "ref": "payment_phone",
                "confidence": 0.95,
            },
            {
                "type": "url",
                "value": "https://scam-payment.example.com/pay",
                "ref": "payment_url",
                "confidence": 1.0,
            },
        ],
    )

    print(f"✓ Added message with identifier refs: {continuation3.id}")
    print(f"  Phone at position {phone_position}, length {phone_length}")
    print(f"  URL at position {url_position}, length {url_length}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"\nParent conversation: {parent.id}")
    print(f"Total continuations: 3")
    print(f"Total messages: 6")
    print(f"Identifiers tracked: 4 (2 participants + 2 discovered)")
    print("\nKey points:")
    print("  - Parent entry holds conversation metadata (platform, type)")
    print("  - Child entries (continuations) hold actual messages")
    print("  - Message indices must be sequential (0, 1, 2, ...)")
    print("  - sender_ref references identifier_lookups by 'ref' field")
    print("  - Use non_contiguous=True for time gaps (shows UI separator)")
    print("  - identifier_refs use byte offsets to mark positions in text")


def calculate_byte_position_example():
    """
    Helper example: Calculate byte positions for identifier references.

    The position and length fields use UTF-8 byte offsets, not character indices.
    This matters for non-ASCII text.
    """
    print("\n" + "=" * 70)
    print("Byte Position Calculation Example")
    print("=" * 70)

    # ASCII text - byte offset equals character offset
    ascii_body = "Call me at +1555123456 please"
    phone = "+1555123456"
    position = ascii_body.encode("utf-8").find(phone.encode("utf-8"))
    length = len(phone.encode("utf-8"))
    print(f"\nASCII: '{ascii_body}'")
    print(f"  Phone '{phone}' at position={position}, length={length}")

    # Unicode text - byte offset differs from character offset!
    unicode_body = "Message: 你好 call +1555123456"
    position_unicode = unicode_body.encode("utf-8").find(b"+1555123456")
    print(f"\nUnicode: '{unicode_body}'")
    print(f"  Phone '+1555123456' at position={position_unicode}")
    print(f"  (Note: position is 18, not 13, because '你好' is 6 bytes in UTF-8)")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see byte position calculation example:
        # calculate_byte_position_example()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
