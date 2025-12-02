# Journal Entries

Journal entries are the core mechanism for submitting scam reports and activities to Scambus.

## Overview

Journal entries record activities performed during fraud investigation and prevention. Each entry has a type (detection, phone_call, email, etc.) and associated details.

## Entry Types

- **Detection**: Automated or manual fraud detection
- **Phone Call**: Scam phone calls
- **Email**: Phishing emails
- **Text Conversation**: SMS/messaging scams
- **Note**: General notes and observations

## Creating Journal Entries

See the [API Reference](../api-reference/client.md) for detailed method documentation.

---

## Text Conversations

Text conversations (SMS, WhatsApp, Telegram, etc.) use a parent-child structure:

1. **Parent entry** (`text_conversation`): Contains metadata about the conversation
2. **Child entries** (`conversation_continuation`): Contain the actual messages

This structure allows adding messages incrementally and tracking conversation history over time.

### Step 1: Create the Parent Conversation

```python
from datetime import datetime
from scambus_client import ScambusClient
from scambus_client.models import TextConversationDetails

client = ScambusClient()

# Create the parent text_conversation entry
parent = client.create_journal_entry(
    entry_type="text_conversation",
    description="WhatsApp scam conversation - tech support fraud",
    details=TextConversationDetails(
        platform="whatsapp",
        conversation_type="individual",
        source_type="export",
        export_format="json",
    ).to_dict(),
    # Define identifiers for participants (referenced in messages via 'ref')
    identifier_lookups=[
        {"type": "phone", "value": "+1555123456", "ref": "scammer", "confidence": 0.9},
        {"type": "phone", "value": "+1555987654", "ref": "victim", "confidence": 1.0},
    ],
)
print(f"Created conversation: {parent.id}")
```

### Step 2: Add Initial Messages (Contiguous)

```python
from scambus_client.models import (
    ConversationContinuationDetails,
    ConversationMessage,
    MessageIdentifierRef,
)

# Create initial batch of messages
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
        body="Please download TeamViewer and give me access code.",
        is_outgoing=False,
        sender_ref="scammer",
    ),
]

# Add as a continuation (child entry)
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
```

### Step 3: Add More Messages Later (Non-Contiguous)

When adding messages that don't immediately follow the previous batch (e.g., hours or days later), use `non_contiguous=True`. This displays a visual separator in the UI.

```python
# Hours later, the conversation continues...
later_messages = [
    ConversationMessage(
        index=3,
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

# Mark as non_contiguous since there's a time gap
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
```

### Step 4: Messages with Detected Identifiers

When messages contain identifiers (phone numbers, emails, URLs, etc.), use `identifier_refs` to mark their positions. This enables clickable links in the UI.

```python
# Message containing a URL and phone number
messages_with_identifiers = [
    ConversationMessage(
        index=5,
        message_id="msg_006",
        timestamp=datetime(2025, 1, 15, 14, 35, 0),
        body="Send the gift cards to this number: +1555999888. Or pay at https://scam-payment.example.com/pay",
        is_outgoing=False,
        sender_ref="scammer",
        # Mark identifier positions in the message body
        identifier_refs=[
            MessageIdentifierRef(
                ref="payment_phone",  # Local reference
                field="body",
                position=37,  # Byte offset where "+1555999888" starts
                length=12,    # Byte length of the identifier
            ),
            MessageIdentifierRef(
                ref="payment_url",
                field="body",
                position=61,  # Byte offset where URL starts
                length=38,
            ),
        ],
    ),
]

# Add continuation with the new identifiers
continuation3 = client.create_journal_entry(
    entry_type="conversation_continuation",
    description="Payment instructions from scammer",
    details=ConversationContinuationDetails(
        messages=messages_with_identifiers,
        reason="payment request",
        non_contiguous=True,  # Still a time gap from previous
    ).to_dict(),
    parent_journal_entry_id=parent.id,
    identifier_lookups=[
        {"type": "phone", "value": "+1555123456", "ref": "scammer"},
        {"type": "phone", "value": "+1555987654", "ref": "victim"},
        # New identifiers discovered in this batch
        {"type": "phone", "value": "+1555999888", "ref": "payment_phone", "confidence": 0.95},
        {"type": "url", "value": "https://scam-payment.example.com/pay", "ref": "payment_url", "confidence": 1.0},
    ],
)
```

### Identifier Position Calculation

The `position` and `length` fields use **byte offsets** (UTF-8 encoded). For ASCII text:

```python
body = "Send the gift cards to this number: +1555999888. Or pay at https://scam-payment.example.com/pay"

# Find byte position of the phone number
phone = "+1555999888"
position = body.encode('utf-8').find(phone.encode('utf-8'))  # 37
length = len(phone.encode('utf-8'))  # 12

# For non-ASCII text, be careful with byte offsets
body_unicode = "Message: 你好 call +1555123456"
position = body_unicode.encode('utf-8').find(b'+1555123456')  # 18 (not 13!)
```

### Key Points

- **Parent-child structure**: Always create a `text_conversation` parent first, then add `conversation_continuation` children
- **Message indices**: Must be sequential integers (0, 1, 2, ...) across the entire conversation
- **`sender_ref`**: References the `ref` field from `identifier_lookups`
- **`non_contiguous`**: Set to `True` when there's a significant time gap (shows visual separator)
- **`identifier_refs`**: Use byte offsets to mark identifier positions in message text
