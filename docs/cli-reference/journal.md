# Journal Commands

Manage journal entries from the command line.

## Commands

- `scambus journal create-detection` - Create a detection entry
- `scambus journal create-phone-call` - Create a phone call entry
- `scambus journal create-email` - Create an email entry
- `scambus journal create-conversation` - Create a text conversation entry
- `scambus journal add-conversation-messages` - Add messages to a conversation
- `scambus journal list` - List journal entries

## Examples

```bash
scambus journal create-detection \
    --description "Phishing email detected" \
    --identifier email:scammer@example.com
```

---

## Text Conversations

### Create a Conversation

```bash
scambus journal create-conversation \
    --description "WhatsApp scam conversation" \
    --platform whatsapp \
    --conversation-type individual \
    --identifier "phone:+1555123456:scammer" \
    --identifier "phone:+1555987654:victim"
```

### Add Initial Messages

```bash
scambus journal add-conversation-messages <conversation_id> \
    --messages-file messages.json \
    --identifier "phone:+1555123456:scammer" \
    --identifier "phone:+1555987654:victim" \
    --reason "initial import"
```

### Add Messages with Time Gap (Non-Contiguous)

Use `--non-contiguous` when messages don't immediately follow the previous batch:

```bash
scambus journal add-conversation-messages <conversation_id> \
    --messages-file later_messages.json \
    --identifier "phone:+1555123456:scammer" \
    --identifier "phone:+1555987654:victim" \
    --reason "messages after time gap" \
    --non-contiguous
```

### Messages JSON Format

```json
[
    {
        "index": 0,
        "message_id": "msg_001",
        "timestamp": "2025-01-15T10:00:00Z",
        "body": "Hello, is this tech support?",
        "is_outgoing": false,
        "sender_ref": "scammer"
    },
    {
        "index": 1,
        "message_id": "msg_002",
        "timestamp": "2025-01-15T10:01:00Z",
        "body": "Yes, how can I help?",
        "is_outgoing": true,
        "sender_ref": "victim"
    }
]
```

### Messages with Identifier References

To mark identifiers within message text:

```json
[
    {
        "index": 2,
        "message_id": "msg_003",
        "timestamp": "2025-01-15T10:02:00Z",
        "body": "Send gift cards to +1555999888",
        "is_outgoing": false,
        "sender_ref": "scammer",
        "identifier_refs": [
            {
                "ref": "payment_phone",
                "field": "body",
                "position": 21,
                "length": 12
            }
        ]
    }
]
```

Note: `position` and `length` are byte offsets (UTF-8 encoded).
