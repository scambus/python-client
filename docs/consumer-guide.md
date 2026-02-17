# Export Stream Consumer Guide

This guide explains how to consume data from a Scambus export stream using the Python client library.

## Prerequisites

Install the Python client:

```bash
pip install git+https://github.com/scambus/python-client.git
```

## Authentication

You need an **API key** (key ID + secret) provided by your Scambus administrator:

```bash
export SCAMBUS_API_KEY_ID="your-key-id"
export SCAMBUS_API_KEY_SECRET="your-secret-key"
```

Or pass them directly when initializing the client (see examples below).

You will also be given a **consumer key** — a UUID that identifies the stream you'll be reading from.

## Consuming via HTTP Polling

HTTP polling is the primary consumption method for data consumers. You request batches of messages on your own schedule using cursor-based pagination.

### Basic Example

```python
from scambus_client import ScambusClient

client = ScambusClient(
    api_key_id="your-key-id",
    api_key_secret="your-secret-key",
)

consumer_key = "your-consumer-key"

# Fetch the first batch of messages (oldest first)
result = client.consume_stream(consumer_key, cursor="0", order="asc", limit=100)

for msg in result.get("messages", []):
    print(msg)

# The response includes a cursor to fetch the next batch
print(result.get("next_cursor"))
print(result.get("has_more"))
```

> **Note:** The `consume_stream()` method's first parameter is named `stream_id`, but you should pass the **consumer key** here — this is what the server uses to identify your stream.

### Continuous Polling Loop

```python
import time
from scambus_client import ScambusClient

client = ScambusClient(
    api_key_id="your-key-id",
    api_key_secret="your-secret-key",
)

consumer_key = "your-consumer-key"
cursor = "0"  # Start from the beginning

while True:
    result = client.consume_stream(
        consumer_key,
        cursor=cursor,
        order="asc",
        limit=100,
    )

    messages = result.get("messages", [])
    for msg in messages:
        process_message(msg)  # Your processing logic here

    # Advance the cursor
    if result.get("next_cursor"):
        cursor = result["next_cursor"]

    # If there are no more messages, wait before polling again
    if not result.get("has_more"):
        time.sleep(5)
```

### Cursor Values

| Cursor | Meaning |
|--------|---------|
| `"0"` | Read from the beginning of the stream |
| `"$"` | Read only new messages arriving after this point |
| `"1735689600000-0"` | Resume from a specific message ID (returned as `cursor` in each message) |

Each message in the response includes a `cursor` field. Save this value to resume from that exact position if your process restarts.

### Polling Response Format

```json
{
  "messages": [ ... ],
  "next_cursor": "1735689600000-5",
  "has_more": true
}
```

> **Note on field defaults:** The `consume_stream()` method defaults to `order="asc"` (oldest first). Pass `order="desc"` for newest first.

## Message Formats

The format of messages depends on the stream's **data type**, which is configured when the stream is created.

### Journal Entry Streams (`data_type: "journal_entry"`)

Each message represents a journal entry event with its associated identifiers:

```json
{
  "message_id": "1735689600000-5",
  "cursor": "1735689600000-5",
  "id": "7c9e6679-...",
  "type": "phone_call",
  "description": "",
  "details": {
    "platform": "pstn",
    "direction": "inbound"
  },
  "performed_at": "2025-10-27T12:35:36.158925Z",
  "confidence": 1,
  "start_time": "2025-10-27T12:35:36.158925Z",
  "end_time": "2025-10-27T12:40:00.000000Z",
  "is_test": false,
  "originator": {
    "id": "f47ac10b-...",
    "type": "user",
    "name": "James D"
  },
  "identifiers": [
    {
      "id": "550e8400-...",
      "type": "phone",
      "display_value": "+12345678888",
      "confidence": 1,
      "is_ours": false,
      "data": { "country_code": "+1", "number": "2345678888" },
      "created_at": "2025-10-27T12:35:36Z",
      "updated_at": "2026-02-06T19:19:18Z"
    }
  ],
  "evidence": [
    {
      "id": "a1b2c3d4-...",
      "type": "screenshot",
      "description": "Screenshot of phishing page",
      "source": "Automated Scanner",
      "collected_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### Identifier Streams (`data_type: "identifier"`)

Each message represents an identifier state change:

```json
{
  "cursor": "1735689600000-5",
  "identifier_id": "550e8400-...",
  "type": "email",
  "display_value": "scammer@example.com",
  "confidence": 0.95,
  "modified_at": "2025-01-15T10:30:00Z",
  "is_test": false,
  "originator_id": "f47ac10b-...",
  "tags": [
    {
      "tag_id": "a1b2c3d4-...",
      "tag_title": "Threat Type",
      "value": "Phishing",
      "value_id": "b2c3d4e5-..."
    }
  ],
  "triggering_journal_entry": {
    "id": "7c9e6679-...",
    "type": "detection",
    "description": "Phishing detected",
    "performed_at": "2025-01-15T10:30:00Z"
  },
  "journal_entries": []
}
```

### Casing Convention

All fields in the consumer API use **snake_case** consistently — both top-level and nested objects.

## Using Typed Stream Message Classes

The Python client provides typed dataclasses for stream messages, so you can work with proper objects instead of raw dicts.

### Typed Stream Messages

```python
from scambus_client import ScambusClient, IdentifierStreamMessage, JournalEntryStreamMessage

client = ScambusClient(api_key_id="your-key-id", api_key_secret="your-secret-key")
result = client.consume_stream("your-consumer-key", cursor="0", limit=100)

# For identifier streams:
for raw_msg in result.get("messages", []):
    msg = IdentifierStreamMessage.from_dict(raw_msg)
    print(f"Identifier: {msg.display_value} (confidence: {msg.confidence})")
    print(f"Type: {msg.type}, Modified: {msg.modified_at}")
    for tag in msg.tags:
        print(f"  Tag: {tag.tag_title} = {tag.value}")

# For journal entry streams:
for raw_msg in result.get("messages", []):
    msg = JournalEntryStreamMessage.from_dict(raw_msg)
    print(f"Entry: {msg.description} ({msg.type})")
    for ident in msg.identifiers:
        print(f"  Identifier: {ident.display_value}")
```

### Typed Identifier Details

Each identifier type has a corresponding details class. Use `parse_identifier_details()` to automatically select the right class:

```python
from scambus_client import (
    IdentifierStreamMessage,
    parse_identifier_details,
    PhoneDetails,
    BankAccountDetails,
)

for raw_msg in result.get("messages", []):
    msg = IdentifierStreamMessage.from_dict(raw_msg)
    details = parse_identifier_details(msg.type, msg.details)

    if isinstance(details, PhoneDetails):
        print(f"Phone: {details.country_code} {details.number}")
        if details.is_toll_free:
            print("  (toll-free)")

    elif isinstance(details, BankAccountDetails):
        print(f"Bank: {details.institution} - {details.account_number}")
```

Available detail classes:

| Type | Class | Key Fields |
|------|-------|------------|
| `phone` | `PhoneDetails` | `country_code`, `number`, `area_code`, `is_toll_free`, `region` |
| `email` | `IdentifierEmailDetails` | `email` |
| `url` | `URLDetails` | `url` |
| `bank_account` | `BankAccountDetails` | `account_number`, `routing`, `institution`, `owner`, `owner_address`, `country`, `address`, `swift`, `iban`, `account_type` |
| `crypto_wallet` | `CryptoWalletDetails` | `address`, `currency`, `network` |
| `social_media` | `SocialMediaDetails` | `platform`, `handle` |
| `zelle` | `ZelleDetails` | `type`, `value` |
| `payment_token` | `PaymentTokenDetails` | `service`, `identifier`, `type` |

All detail classes support both snake_case and camelCase input via `from_dict()`, and output snake_case via `to_dict()`.

## Consuming via SSE (Server-Sent Events)

For real-time consumption with lower latency, you can connect to the SSE endpoint directly. This keeps a persistent HTTP connection open and pushes messages to you as they arrive.

The SSE endpoint is:

```
GET /api/consume/{consumer_key}/stream?cursor=$&include_test=false
```

### SSE with Python (`sseclient-py`)

```bash
pip install sseclient-py requests
```

```python
import json
import requests
import sseclient

consumer_key = "your-consumer-key"
api_url = "https://scambus.net/api"
api_key_id = "your-key-id"
api_key_secret = "your-secret-key"

url = f"{api_url}/consume/{consumer_key}/stream"
headers = {
    "X-API-Key": f"{api_key_id}:{api_key_secret}",
    "Accept": "text/event-stream",
}
params = {
    "cursor": "$",           # "$" = new messages only, "0" = from beginning
    "include_test": "false",
}

response = requests.get(url, headers=headers, params=params, stream=True)
client = sseclient.SSEClient(response)

for event in client.events():
    if event.event == "connected":
        info = json.loads(event.data)
        print(f"Connected to stream: {info['stream']}")

    elif event.event == "batch":
        # Initial historical replay — array of messages
        messages = json.loads(event.data)
        for msg in messages:
            process_message(msg)

    elif event.event == "message":
        # Real-time individual message
        msg = json.loads(event.data)
        process_message(msg)

    elif event.event == "error":
        error = json.loads(event.data)
        print(f"Error: {error['error']}")
```

### SSE Event Types

| Event | Description |
|-------|-------------|
| `connected` | Sent immediately on connection. Contains stream metadata. |
| `batch` | Array of messages during initial historical replay. |
| `message` | Individual real-time message after replay is complete. |
| `error` | Error notification. |
| `: heartbeat` | Keepalive comment sent every ~15 seconds (not a named event — most SSE clients handle this automatically). |

### SSE Reconnection

If the connection drops, reconnect with the `cursor` set to the last `cursor` value you received from a message. This ensures you resume without gaps or duplicates.

## Consuming via CLI (Quick Testing)

The CLI is useful for verifying your stream is working:

```bash
# Poll for messages
scambus streams consume YOUR-CONSUMER-KEY --limit 10 --json

# Real-time listening via SSE
scambus streams listen YOUR-CONSUMER-KEY --json

# Get stream metadata
scambus streams info YOUR-CONSUMER-KEY
```

## Error Handling

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| 401 | Invalid API key or inactive stream | Check your credentials and consumer key |
| 403 | Insufficient permissions | Contact the stream owner |
| 410 | Cursor is outside the retention window | Reset cursor to `"0"` or `"$"` |
| 416 | Cursor is before stream start (data trimmed) | Use the `stream_first_id` from the error response, or `"0"` |
| 429 | Rate limited | Back off and retry after a delay |
| 503 | Stream is being rebuilt | Retry after ~10 seconds |

## Getting Stream Information

You can inspect stream metadata (available cursors, message count, etc.) via the info endpoint:

```
GET /api/consume/{consumer_key}/info
```

Or with curl:

```bash
curl -H "X-API-Key: YOUR_KEY_ID:YOUR_SECRET" \
  "https://scambus.net/api/consume/YOUR-CONSUMER-KEY/info"
```

This returns cursor positions, message counts, and other stream metadata to help you choose a starting cursor.
