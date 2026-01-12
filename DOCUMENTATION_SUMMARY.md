# Scambus Python Client - Complete Documentation

Official Python client for SCAMBUS - submit scam reports and subscribe to data streams.

**Package:** `scambus` | **Version:** 0.1.0 | **Python:** 3.8+

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Authentication](#3-authentication)
4. [Quick Start](#4-quick-start)
5. [Core Features](#5-core-features)
   - [5.1 Journal Entries](#51-journal-entries-scam-reports)
   - [5.2 Export Streams](#52-export-streams)
   - [5.3 Identifier Structured Data](#53-identifier-structured-data)
   - [5.4 Search](#54-search)
   - [5.5 Views (Saved Queries)](#55-views-saved-queries)
   - [5.6 Case Management](#56-case-management)
   - [5.7 Tags](#57-tags)
   - [5.8 Media & Evidence](#58-media--evidence)
   - [5.9 Automation Management](#59-automation-management)
   - [5.10 Real-time Notifications](#510-real-time-notifications-websocket)
6. [CLI Reference](#6-cli-reference)
7. [API Reference](#7-api-reference)
8. [Error Handling](#8-error-handling)
9. [Development](#9-development)
10. [Examples](#10-examples)
11. [Appendices](#11-appendices)

---

## 1. Overview

### What is Scambus?

Scambus is a collaborative scam reporting and fraud intelligence platform. The Python client provides programmatic access to:

- **Submit Scam Reports**: Phone calls, emails, text messages, detections, and more
- **Tagging**: Apply boolean and valued tags when creating journal entries
- **Search**: Find identifiers, cases, and journal entries
- **Views (Saved Queries)**: Create, execute, and manage saved query views
- **In-Progress Activities**: Track and complete ongoing scam interactions
- **Data Streams**: Subscribe to real-time scam data with export streams
- **Real-time Notifications**: WebSocket support for instant notifications
- **Case Management**: Create and manage investigation cases
- **Evidence**: Upload and attach media evidence
- **Automation Management**: Create automation identities with API key rotation

### Package Components

The `scambus` package includes:

| Component | Description |
|-----------|-------------|
| `scambus_client` | Python SDK library |
| `scambus` CLI | Command-line interface tool |

---

## 2. Installation

### From GitHub (Primary Method)

```bash
# Install latest from main branch
pip install git+https://github.com/scambus/python-client.git

# Install specific version/tag
pip install git+https://github.com/scambus/python-client.git@v0.1.0

# Install specific branch
pip install git+https://github.com/scambus/python-client.git@feature-branch
```

### Verification

```bash
# Check CLI is installed
scambus --version

# Check SDK is importable
python -c "from scambus_client import ScambusClient; print('OK')"
```

---

## 3. Authentication

### Configuration Storage

Credentials are stored at:
- **Location**: `~/.scambus/config.json`
- **Permissions**: `0600` (read/write for owner only)
- **Shared**: Automatically used by both CLI and SDK

### Method 1: Device Authorization Flow (Recommended for Interactive Use)

Best for personal accounts and interactive CLI usage. Uses OAuth 2.0 Device Authorization Grant.

```bash
# Start interactive login (opens browser)
scambus auth login
```

**How it works:**
1. CLI displays a verification URL and user code
2. Open the URL in your browser and enter the code
3. After authorization, CLI receives JWT access token + refresh token
4. Credentials are cached at `~/.scambus/config.json`
5. Access tokens auto-refresh when expired

**Config structure:**
```json
{
  "auth": {
    "type": "device",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "...",
    "expires_at": 1737244800.0
  }
}
```

### Method 2: API Key Authentication (For Automation)

Best for automation, CI/CD pipelines, and programmatic access.

```bash
# Login with API key (obtain from web UI first)
scambus auth login --api-key "your-api-key-from-web-ui"
```

**Config structure:**
```json
{
  "auth": {
    "type": "apikey",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "api_key": "your-api-key-from-web-ui"
  }
}
```

### SDK Authentication

The SDK automatically loads credentials from the CLI's config file:

```python
from scambus_client import ScambusClient

# No parameters needed - auto-loads from ~/.scambus/config.json
client = ScambusClient()
```

**Loading priority:**
1. Explicit parameters: `ScambusClient(api_token="...")`
2. Environment variables: `SCAMBUS_API_TOKEN`, `SCAMBUS_URL`
3. Config file: `~/.scambus/config.json`
4. Defaults: `https://scambus.net/api`

**Override for development:**
```python
# Local development
client = ScambusClient(api_url="http://localhost:8080/api")

# Custom token
client = ScambusClient(api_token="custom-jwt-token")

# Both
client = ScambusClient(
    api_url="http://localhost:8080/api",
    api_token="custom-jwt-token"
)
```

### Environment Variables

```bash
export SCAMBUS_URL="https://scambus.net"
export SCAMBUS_API_TOKEN="your-jwt-token"
```

### Token Lifecycle

**Device Flow:**
- Access tokens expire (typically 1 hour)
- Refresh tokens automatically renew access tokens
- CLI/SDK auto-refreshes transparently
- Refresh tokens are long-lived

**API Key:**
- API keys don't expire
- JWT tokens returned are used for API calls
- Re-authenticate if token becomes invalid

---

## 4. Quick Start

### Initialize Client

```python
from scambus_client import ScambusClient, TagLookup

# Auto-loads credentials from CLI config
client = ScambusClient()
```

### Submit a Scam Detection

```python
# With typed tags (recommended)
detection = client.create_detection(
    description="Phishing email pretending to be from bank",
    identifiers=["email:scammer@example.com"],
    confidence=0.9,
    tags=[
        TagLookup(tag_name="Phishing"),
        TagLookup(tag_name="ScamType", tag_value="Banking")
    ]
)
print(f"Created: {detection.id}")
```

### Track an Ongoing Phone Call

```python
from datetime import datetime

# Start tracking (in_progress=True means no end_time yet)
call = client.create_phone_call(
    description="Tech support scam in progress",
    direction="inbound",
    start_time=datetime.now(),
    identifiers=["phone:+1234567890"],
    in_progress=True
)

# Later... complete the activity
client.complete_activity(
    call.id,
    end_time=datetime.now(),
    completion_reason="manual",
    description="Scammer hung up after being questioned"
)
```

### Search for Identifiers

```python
results = client.search_identifiers(
    query="+1234567890",
    identifier_type="phone"
)
```

### Create and Consume a Stream

```python
# Create stream for phone scams
stream = client.create_stream(
    name="Phone Scams Monitor",
    data_type="journal_entry",
    identifier_types=["phone"],
    min_confidence=0.8
)

# Consume messages
result = client.consume_stream(stream.id, cursor="0", limit=10)
for msg in result['messages']:
    print(f"New phone scam: {msg['type']}")
```

---

## 5. Core Features

### 5.1 Journal Entries (Scam Reports)

Journal entries are the core mechanism for submitting scam reports.

#### Entry Types

| Type | Description | Method |
|------|-------------|--------|
| `detection` | Automated or manual scam detections | `create_detection()` |
| `phone_call` | Scam phone calls | `create_phone_call()` |
| `email` | Phishing or scam emails | `create_email()` |
| `text_conversation` | SMS or messaging app scams | `create_text_conversation()` |
| `note` | General observations | `create_note()` |
| `import` | Data from external source | `create_import()` |
| `export` | Export findings | `create_export()` |

#### Creating Entries with Tags

**SDK - Typed tags (recommended):**
```python
from scambus_client import TagLookup

client.create_detection(
    description="Ransomware detected",
    identifiers=["email:scam@example.com"],
    tags=[
        TagLookup(tag_name="Malware"),                           # Boolean tag
        TagLookup(tag_name="ScamType", tag_value="Ransomware")   # Valued tag
    ]
)
```

**SDK - Dictionary tags (backward compatible):**
```python
client.create_detection(
    description="Ransomware detected",
    identifiers=["email:scam@example.com"],
    tags=[
        {"tag_name": "Malware"},
        {"tag_name": "ScamType", "tag_value": "Ransomware"}
    ]
)
```

**CLI:**
```bash
# Boolean tags
scambus journal create-detection \
    --description "Ransomware detected" \
    --identifier email:scam@example.com \
    --tag "Malware" \
    --tag "HighPriority"

# Valued tags (use colon separator)
scambus journal create-detection \
    --description "Phishing campaign" \
    --tag "ScamType:Phishing" \
    --tag "Industry:Banking"
```

#### Identifier Validation and Failed Identifiers

When creating journal entries, identifiers are validated based on their type:
- **phone**: Must be E.164 format (e.g., `+12025551234`)
- **email**: Must be valid RFC email format
- **url**: Must be valid URL format

If an identifier fails validation, the journal entry is **still created** - only the invalid identifier is skipped. The `failed_identifiers` field on the returned entry contains details about any skipped identifiers:

```python
from scambus_client import ScambusClient, IdentifierLookup, FailedIdentifier

client = ScambusClient()

# Create detection with mix of valid and invalid identifiers
entry = client.create_detection(
    description="Suspicious activity detected",
    identifiers=[
        IdentifierLookup(type="phone", value="+12025551234"),  # Valid
        IdentifierLookup(type="phone", value="555-1234"),      # Invalid format
        IdentifierLookup(type="email", value="test@example.com"),  # Valid
        IdentifierLookup(type="email", value="not-an-email"),  # Invalid format
    ],
)

# Entry is created successfully with valid identifiers
print(f"Created entry: {entry.id}")
print(f"Valid identifiers: {len(entry.identifiers)}")  # 2

# Check for any identifiers that failed validation
if entry.failed_identifiers:
    print(f"\nWarning: {len(entry.failed_identifiers)} identifier(s) failed validation:")
    for failed in entry.failed_identifiers:
        print(f"  - {failed.type}={failed.value}: {failed.reason}")
```

**Output:**
```
Created entry: abc-123-def
Valid identifiers: 2

Warning: 2 identifier(s) failed validation:
  - phone=555-1234: phone number must be in E.164 format (e.g., +1234567890)
  - email=not-an-email: invalid email format
```

**Key points:**
- Journal entry creation succeeds even if some identifiers fail validation
- `failed_identifiers` is `None` when all identifiers are valid
- `failed_identifiers` is only populated on entries returned from `create_*` methods, not from `get_journal_entry()`
- The `FailedIdentifier` type has `type`, `value`, and `reason` fields

#### In-Progress Activities

Track ongoing scam interactions:

```python
# Create in-progress activity (no end_time)
call = client.create_phone_call(
    description="Ongoing scam call",
    direction="inbound",
    start_time=datetime.now(),
    in_progress=True
)

# Get all in-progress activities
activities = client.get_in_progress_activities()

# Complete an activity later
client.complete_activity(
    call.id,
    end_time=datetime.now(),
    completion_reason="manual",
    description="Call completed - scammer identified"
)
```

**CLI:**
```bash
# View in-progress activities
scambus journal in-progress
```

#### Text Conversations (Parent-Child Structure)

Text conversations use a parent-child structure for incremental message addition:

1. **Parent entry** (`text_conversation`): Contains metadata
2. **Child entries** (`conversation_continuation`): Contain messages

```python
from scambus_client.models import (
    TextConversationDetails,
    ConversationContinuationDetails,
    ConversationMessage,
    MessageIdentifierRef,
)

# Step 1: Create parent conversation
parent = client.create_journal_entry(
    entry_type="text_conversation",
    description="WhatsApp scam - tech support fraud",
    details=TextConversationDetails(
        platform="whatsapp",
        conversation_type="individual",
        source_type="export",
        export_format="json",
    ).to_dict(),
    identifier_lookups=[
        {"type": "phone", "value": "+1555123456", "ref": "scammer", "confidence": 0.9},
        {"type": "phone", "value": "+1555987654", "ref": "victim", "confidence": 1.0},
    ],
)

# Step 2: Add messages as continuation
messages = [
    ConversationMessage(
        index=0,
        message_id="msg_001",
        timestamp=datetime(2025, 1, 15, 10, 0, 0),
        body="Hello, this is Microsoft Support. Your computer has a virus.",
        is_outgoing=False,
        sender_ref="scammer",
    ),
    ConversationMessage(
        index=1,
        message_id="msg_002",
        timestamp=datetime(2025, 1, 15, 10, 1, 30),
        body="Oh no! What should I do?",
        is_outgoing=True,
        sender_ref="victim",
    ),
]

continuation = client.create_journal_entry(
    entry_type="conversation_continuation",
    description="Initial messages",
    details=ConversationContinuationDetails(
        messages=messages,
        reason="initial import",
    ).to_dict(),
    parent_journal_entry_id=parent.id,
    identifier_lookups=[
        {"type": "phone", "value": "+1555123456", "ref": "scammer"},
        {"type": "phone", "value": "+1555987654", "ref": "victim"},
    ],
)

# Step 3: Add later messages (non-contiguous shows visual separator)
later_messages = [
    ConversationMessage(
        index=2,
        message_id="msg_003",
        timestamp=datetime(2025, 1, 15, 14, 30, 0),  # Hours later
        body="Please send $500 in gift cards.",
        is_outgoing=False,
        sender_ref="scammer",
    ),
]

client.create_journal_entry(
    entry_type="conversation_continuation",
    description="Later messages",
    details=ConversationContinuationDetails(
        messages=later_messages,
        reason="additional messages",
        non_contiguous=True,  # Shows visual separator
    ).to_dict(),
    parent_journal_entry_id=parent.id,
    identifier_lookups=[...],
)
```

**Key points:**
- Message indices must be sequential (0, 1, 2, ...)
- `sender_ref` references `identifier_lookups` by `ref` field
- Use `non_contiguous=True` for time gaps
- `identifier_refs` use byte offsets for identifier positions in text

---

### 5.2 Export Streams

Subscribe to real-time scam data with two types of streams.

#### Stream Types

| Feature | Journal Entry Stream | Identifier Stream |
|---------|---------------------|-------------------|
| Data Type | `journal_entry` | `identifier` |
| Publishes | Complete journal entries | Identifier state changes |
| Frequency | Every matching JE | Only on state change |
| Contains | JE + all identifiers + evidence | Identifier state + triggering JE |
| Backfill | Not supported | Supported |
| Use Case | Track all scam events | Track identifier evolution |

#### Creating Streams

**Journal Entry Stream:**
```python
stream = client.create_stream(
    name="High-Confidence Phone Scams",
    data_type="journal_entry",
    identifier_types=["phone"],
    min_confidence=0.8,
    max_confidence=1.0
)
```

**Identifier Stream with Backfill:**
```python
stream = client.create_stream(
    name="Phone Number State Changes",
    data_type="identifier",
    identifier_types=["phone"],
    min_confidence=0.9,
    backfill_historical=True,
    backfill_from_date="2025-01-01T00:00:00Z"
)
```

#### Filter Helpers

Helper functions simplify JSONPath filter expressions:

**`build_identifier_type_filter()`**
```python
from scambus_client import build_identifier_type_filter

# Single type
filter_expr = build_identifier_type_filter("phone")
# Result: '$.type == "phone"'

# Multiple types
filter_expr = build_identifier_type_filter(["phone", "email"])
# Result: '$.type == "phone" || $.type == "email"'
```

**`build_combined_filter()`**
```python
from scambus_client import build_combined_filter

# Type + minimum confidence
filter_expr = build_combined_filter(
    identifier_types="phone",
    min_confidence=0.8
)
# Result: '$.type == "phone" && $.confidence >= 0.8'

# Multiple types + confidence range + custom filter
filter_expr = build_combined_filter(
    identifier_types=["phone", "email"],
    min_confidence=0.9,
    max_confidence=1.0,
    custom_expression='$.details.verified == true'
)
```

#### Using Filters with create_stream()

```python
# Simple: use identifier_types parameter
stream = client.create_stream(
    name="Phone Numbers Only",
    data_type="identifier",
    identifier_types="phone",
    min_confidence=0.8
)

# Advanced: combine with custom expression
stream = client.create_stream(
    name="WhatsApp Only",
    data_type="identifier",
    identifier_types="social_media",
    filter_expression='$.details.platform == "whatsapp"',
    min_confidence=0.85
)
```

#### Consuming Streams

```python
result = client.consume_stream(stream.id, cursor="0", limit=100)

for msg in result['messages']:
    if stream.data_type == "journal_entry":
        print(f"Journal Entry: {msg['type']} - {msg['description']}")
    else:
        print(f"Identifier: {msg['type']} - {msg['displayValue']}")
        print(f"Confidence: {msg['confidence']}")
        print(f"Triggered by: {msg['triggeringJournalEntry']['type']}")

# Save cursor for next poll
next_cursor = result['cursor']
```

#### Stream Management

```python
# Recover from Redis failures
client.recover_stream(stream.id, ignore_checkpoint=False, clear_stream=True)

# Backfill historical data (identifier streams only)
client.backfill_stream(stream.id, from_date="2025-01-01T00:00:00Z")

# Check recovery status
status = client.get_recovery_status()
for log in status['logs']:
    print(f"{log['streamName']}: {log.get('completedAt', 'In Progress')}")
```

**CLI:**
```bash
# Create journal entry stream
scambus streams create \
    --name "High Confidence Detections" \
    --data-type journal_entry \
    --min-confidence 0.9

# Create identifier stream with backfill
scambus streams create \
    --name "Phone State Changes" \
    --data-type identifier \
    --identifier-type phone \
    --min-confidence 0.8 \
    --backfill \
    --backfill-from-date 2025-01-01T00:00:00Z

# Consume from stream
scambus streams consume <stream-id> --limit 100
```

---

### 5.3 Identifier Structured Data

When consuming identifier streams, each message includes a `details` field with type-specific structured data.

#### Message Structure

```json
{
  "identifier_id": "uuid",
  "type": "phone|email|bank_account|crypto_wallet|social_media|zelle",
  "display_value": "normalized display value",
  "confidence": 0.0-1.0,
  "details": { ... },
  "tags": [...],
  "triggering_journal_entry": {...}
}
```

#### Phone Numbers

**Type:** `phone` | **Display Value:** E.164 format (e.g., `+12345678901`)

```json
{
  "country_code": "+1",
  "number": "2345678901",
  "area_code": "234",
  "is_toll_free": false,
  "region": "US"
}
```

**Example:**
```python
details = msg.get("details", {})
country_code = details.get('country_code') or details.get('countryCode')
area_code = details.get('area_code') or details.get('areaCode')
is_toll_free = details.get('is_toll_free', details.get('isTollFree', False))

if is_toll_free and confidence > 0.9:
    add_to_toll_free_scam_list(msg['displayValue'])
```

#### Email Addresses

**Type:** `email` | **Display Value:** Lowercase email

```json
{
  "email": "user@example.com"
}
```

#### Bank Accounts

**Type:** `bank_account`

```json
{
  "account_number": "1234567890",
  "routing": "021000021",
  "institution": "Example Bank",
  "owner": "John Doe",
  "owner_address": "123 Main St",
  "country": "US",
  "routing_bank": "Federal Reserve",
  "account_type": "checking"
}
```

#### Cryptocurrency Wallets

**Type:** `crypto_wallet`

```json
{
  "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
  "currency": "BTC",
  "network": "mainnet"
}
```

#### Social Media Handles

**Type:** `social_media` | **Display Value:** `@platform:username`

```json
{
  "platform": "twitter",
  "handle": "username"
}
```

#### Zelle Identifiers

**Type:** `zelle`

```json
{
  "type": "email|phone",
  "value": "user@example.com"
}
```

#### Field Name Formats

The API may return field names in either snake_case or camelCase. Handle both:

```python
country_code = details.get('country_code') or details.get('countryCode')
area_code = details.get('area_code') or details.get('areaCode')
is_toll_free = details.get('is_toll_free', details.get('isTollFree', False))
```

---

### 5.4 Search

```python
# Search identifiers
identifiers = client.search_identifiers(
    query="example.com",
    identifier_type="email"
)

# Search cases
cases = client.search_cases(
    query="phishing",
    status="open"
)

# Advanced journal entry search
entries = client.query_journal_entries(
    search_query="scam",
    entry_type="phone_call",
    min_confidence=0.7,
    performed_after="2025-01-01T00:00:00Z"
)
```

**CLI:**
```bash
scambus search identifiers --query "+1234567890"
scambus search cases --query "phishing"
```

---

### 5.5 Views (Saved Queries)

```python
# Execute system views
my_journal = client.execute_my_journal_entries(limit=20)
pinned = client.execute_my_pinboard(limit=10)

# List custom views
views = client.list_views()

# Execute custom view
result = client.execute_view(view_id, limit=20)

# Create custom view with typed filters
from scambus_client import ViewFilter, ViewSortOrder

view = client.create_view(
    name="High Confidence Detections",
    entity_type="journal",
    filter_criteria=ViewFilter(
        min_confidence=0.9,
        entry_types=["detection"]
    ),
    sort_order=ViewSortOrder(field="created_at", direction="desc"),
    visibility="organization"
)
```

**CLI:**
```bash
scambus views list
scambus views my-journal
scambus views my-pinboard
scambus views execute VIEW_ID --limit 20
scambus views create \
    --name "High Confidence Phone Scams" \
    --entity-type journal \
    --filter-criteria '{"identifier_types": ["phone"], "min_confidence": 0.9}'
```

---

### 5.6 Case Management

```python
# Create a case
case = client.create_case(
    title="Phishing Campaign Investigation",
    description="Coordinated phishing targeting bank customers",
    status="open"
)

# Update status
client.update_case(case.id, status="in_progress")

# Add comments
client.create_case_comment(
    case.id,
    comment="Found 15 related identifiers"
)

# List cases
cases = client.list_cases(status="open")
```

---

### 5.7 Tags

```python
# List available tags
tags = client.list_tags()

# Create a tag
tag = client.create_tag(
    name="High Priority",
    tag_type="priority"
)

# Get effective tags for an entity
effective = client.get_effective_tags(entity_type="identifier", entity_id=id)
```

---

### 5.8 Media & Evidence

```python
# Upload media file
media = client.upload_media(
    file_path="screenshot.png",
    notes="Screenshot of phishing site"
)

# Upload from buffer
media = client.upload_media_from_buffer(
    buffer=image_bytes,
    filename="capture.png",
    content_type="image/png"
)

# Attach to journal entry
client.create_detection(
    description="Phishing site",
    identifiers=["url:https://scam-site.com"],
    evidence={"media_ids": [media.id]}
)
```

**CLI:**
```bash
scambus media upload screenshot.png --notes "Screenshot of phishing site"
```

---

### 5.9 Automation Management

Create dedicated automation accounts for scripts:

```bash
# Login as yourself first
scambus auth login

# Create an automation
scambus automations create --name "Phishing Detector Bot" \
    --description "Automated phishing detection"

# Create API key and switch to it
scambus automations create-key "Phishing Detector Bot" --assume
# Output: key_abc123:secret_xyz789
# Now operating as automation

# Run your script (uses automation credentials)
python my_detector.py

# Switch back to personal account
scambus auth login
```

**SDK:**
```python
# Create automation
automation = client.create_automation(
    name="Phishing Detector",
    description="Automated phishing detection bot"
)

# Create API key
key_data = client.create_automation_api_key(
    automation_id=automation["id"],
    name="Production Key"
)
api_key = f"{key_data['accessKeyId']}:{key_data['secretAccessKey']}"

# Manage keys
keys = client.list_automation_api_keys(automation["id"])
client.revoke_automation_api_key(automation["id"], key_id)
client.delete_automation_api_key(automation["id"], key_id)
```

**Key rotation workflow:**
1. Create new key: `scambus automations create-key "Bot Name" --name "New Key"`
2. Update scripts with new key
3. Test the new key
4. Revoke old key: `scambus automations revoke-key AUTOMATION_ID OLD_KEY_ID`

---

### 5.10 Real-time Notifications (WebSocket)

```python
import asyncio
from scambus_client import ScambusClient

client = ScambusClient()
ws_client = client.create_websocket_client()

async def handle_notification(notification):
    print(f"New notification: {notification['title']}")
    print(f"Message: {notification['message']}")

asyncio.run(ws_client.listen_notifications(handle_notification))
```

See `examples/websocket_notifications.py` and `examples/websocket_custom_handlers.py` for advanced usage.

---

## 6. CLI Reference

### Authentication Commands

```bash
scambus auth login                           # Interactive device flow
scambus auth login --api-key "KEY"           # API key authentication
scambus auth status                          # Check auth status
scambus auth logout                          # Remove credentials
```

### Journal Commands

```bash
scambus journal create-detection --description "..." --identifier TYPE:VALUE [--tag TAG] [--confidence 0.9]
scambus journal create-phone-call --description "..." --direction inbound|outbound --phone "+1234567890" [--platform pstn]
scambus journal create-email --description "..." --from "from@example.com" --to "to@example.com"
scambus journal create-text --description "..." --platform whatsapp
scambus journal create-note --description "..."
scambus journal query --search "query" [--limit 20]
scambus journal in-progress
```

### Stream Commands

```bash
scambus streams create --name "Name" --data-type journal_entry|identifier [--identifier-type phone] [--min-confidence 0.8]
scambus streams list
scambus streams consume STREAM_ID [--limit 100]
scambus streams recover STREAM_ID
scambus streams backfill STREAM_ID --from-date 2025-01-01T00:00:00Z
```

### Search Commands

```bash
scambus search identifiers --query "QUERY" [--type phone|email|url]
scambus search cases --query "QUERY" [--status open|closed]
```

### View Commands

```bash
scambus views list
scambus views my-journal
scambus views my-pinboard
scambus views execute VIEW_ID [--limit 20]
scambus views create --name "Name" --entity-type journal --filter-criteria '{...}'
```

### Case Commands

```bash
scambus cases list [--status open]
scambus cases create --title "Title" --description "..."
scambus cases get CASE_ID
scambus cases update CASE_ID --status in_progress
```

### Profile Commands

```bash
scambus profile notifications
scambus profile sessions
scambus profile passkeys
scambus profile twofa --enable|--disable
```

### Automation Commands

```bash
scambus automations list
scambus automations create --name "Name" --description "..."
scambus automations create-key "Name" [--name "Key Name"] [--assume]
scambus automations list-keys AUTOMATION_ID
scambus automations revoke-key AUTOMATION_ID KEY_ID
scambus automations delete-key AUTOMATION_ID KEY_ID
```

---

## 7. API Reference

### ScambusClient Constructor

```python
ScambusClient(
    api_url: str = None,          # API URL (default: https://scambus.net/api)
    api_token: str = None,        # JWT token
    api_key_id: str = None,       # API key ID (alternative auth)
    api_key_secret: str = None,   # API key secret (alternative auth)
    timeout: int = 30,            # Request timeout in seconds
    max_retries: int = 3,         # Max retry attempts
)
```

### Input Types

**TagLookup**
```python
from scambus_client import TagLookup

TagLookup(tag_name="TagName")                        # Boolean tag
TagLookup(tag_name="TagName", tag_value="Value")     # Valued tag
```

**ViewFilter**
```python
from scambus_client import ViewFilter

ViewFilter(
    min_confidence=0.9,
    entry_types=["detection", "phone_call"],
    identifier_types=["phone", "email"],
)
```

**ViewSortOrder**
```python
from scambus_client import ViewSortOrder

ViewSortOrder(field="created_at", direction="desc")
```

**StreamFilter**
```python
from scambus_client import StreamFilter

StreamFilter(
    identifier_types=["phone"],
    min_confidence=0.8,
    max_confidence=1.0,
)
```

### Key Methods

| Category | Methods |
|----------|---------|
| **Journal Entries** | `create_detection()`, `create_phone_call()`, `create_email()`, `create_text_conversation()`, `create_note()`, `create_import()`, `create_export()`, `get_journal_entry()`, `delete_journal_entry()`, `list_journal_entries()`, `query_journal_entries()` |
| **In-Progress** | `get_in_progress_activities()`, `complete_activity()` |
| **Streams** | `create_stream()`, `list_streams()`, `get_stream()`, `delete_stream()`, `consume_stream()`, `recover_stream()`, `backfill_stream()`, `get_recovery_status()`, `get_stream_recovery_info()` |
| **Search** | `search_identifiers()`, `search_cases()`, `list_identifiers()` |
| **Views** | `create_view()`, `list_views()`, `get_view()`, `delete_view()`, `execute_view()`, `execute_my_journal_entries()`, `execute_my_pinboard()` |
| **Cases** | `create_case()`, `list_cases()`, `get_case()`, `update_case()`, `delete_case()`, `create_case_comment()` |
| **Tags** | `create_tag()`, `list_tags()`, `get_tag()`, `update_tag()`, `delete_tag()`, `get_effective_tags()` |
| **Media** | `upload_media()`, `upload_media_from_buffer()`, `get_media()` |
| **Profile** | `list_notifications()`, `mark_notification_as_read()`, `list_sessions()`, `list_passkeys()`, `get_2fa_status()`, `toggle_2fa()` |
| **Automations** | `create_automation()`, `list_automations()`, `create_automation_api_key()`, `list_automation_api_keys()`, `revoke_automation_api_key()`, `delete_automation_api_key()` |
| **Reports** | `generate_identifier_report()`, `generate_journal_entry_report()`, `generate_view_report()`, `get_report_status()`, `download_report()`, `wait_for_report()` |
| **WebSocket** | `create_websocket_client()` |
| **Helpers** | `build_identifier_type_filter()`, `build_combined_filter()`, `build_stream_filter()` |

---

## 8. Error Handling

```python
from scambus_client import (
    ScambusClient,
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusValidationError,
    ScambusNotFoundError,
    ScambusServerError,
)

try:
    entry = client.create_detection(...)
except ScambusAuthenticationError:
    print("Invalid API key or token expired")
except ScambusValidationError as e:
    print(f"Validation error: {e}")
except ScambusNotFoundError:
    print("Resource not found")
except ScambusServerError as e:
    print(f"Server error (5xx): {e}")
except ScambusAPIError as e:
    print(f"API error: {e.status_code} - {e.response_data}")
```

**Exception Hierarchy:**
- `ScambusAPIError` - Base exception (has `status_code`, `response_data`)
  - `ScambusAuthenticationError` - 401 errors
  - `ScambusValidationError` - 400 errors
  - `ScambusNotFoundError` - 404 errors
  - `ScambusServerError` - 5xx errors

---

## 9. Development

### Setup Environment

```bash
git clone https://github.com/scambus/python-client.git
cd scambus-python-client
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Unit tests
pytest tests/ -m "not integration"

# With coverage
pytest tests/ -m "not integration" --cov=scambus_client --cov=scambus_cli

# Integration tests
export SCAMBUS_TEST_URL="https://test-api.scambus.net"
export SCAMBUS_TEST_API_KEY="test-key"
pytest tests/integration/ -m integration
```

### Code Quality

```bash
# Format code
black scambus_client/ scambus_cli/ tests/
isort scambus_client/ scambus_cli/ tests/

# Lint
ruff check scambus_client/ scambus_cli/ tests/
mypy scambus_client/ scambus_cli/

# Security scan
bandit -r scambus_client/ scambus_cli/

# All checks
pre-commit run --all-files
```

### Building Documentation

```bash
pip install mkdocs mkdocs-material mkdocstrings[python]
mkdocs serve    # Local development
mkdocs build    # Build static site
```

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat(client): add bulk journal entry creation
fix(streams): handle empty cursor in consume_stream
docs(readme): update installation instructions
test(models): add tests for in-progress activities
```

---

## 10. Examples

Complete working examples are in the [`examples/`](examples/) directory:

### Journal Entry Examples

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`simple_detection.py`](examples/simple_detection.py) | Basic phishing detection with identifiers | `create_detection()`, identifier dictionaries, details field |
| [`detection_with_evidence.py`](examples/detection_with_evidence.py) | Detection with screenshot evidence | `upload_media()`, evidence attachment, media workflow |
| [`phone_call_example.py`](examples/phone_call_example.py) | Report inbound/outbound scam calls | `create_phone_call()`, direction, recording_url, transcript_url |
| [`email_example.py`](examples/email_example.py) | Report phishing emails | `create_email()`, headers, attachments, HTML body |
| [`text_conversation_example.py`](examples/text_conversation_example.py) | Simple text conversation (SMS/WhatsApp) | `create_text_conversation()`, platform support |
| [`text_conversation_with_continuation.py`](examples/text_conversation_with_continuation.py) | **Full conversation with message history** | Parent-child structure, `conversation_continuation`, `ConversationMessage`, `MessageIdentifierRef`, non-contiguous messages, byte position calculation |
| [`bank_account_detection.py`](examples/bank_account_detection.py) | Bank transfer fraud detection | `create_bank_account_identifier()`, financial identifiers |

### In-Progress Activities

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`in_progress_activity_example.py`](examples/in_progress_activity_example.py) | Track ongoing scam interactions | `in_progress=True`, `complete_activity()`, `.complete()` method, completion reasons |

### Export Streams

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`stream_management.py`](examples/stream_management.py) | Create and consume journal entry streams | `create_stream()`, `consume_stream()`, cursor pagination, recovery |
| [`identifier_stream_example.py`](examples/identifier_stream_example.py) | Identifier state change streams with backfill | `data_type="identifier"`, `backfill_historical`, structured data extraction |

### Case Management

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`case_management.py`](examples/case_management.py) | Investigation case workflow | `create_case()`, `update_case()`, `list_cases()`, status management |

### Media & Evidence

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`simple_media_upload.py`](examples/simple_media_upload.py) | Upload evidence files | `upload_media()`, single/multiple files, `media=` parameter |

### Views (Saved Queries)

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`views_example.py`](examples/views_example.py) | Create and execute saved query views | `create_view()`, `execute_view()`, `ViewFilter`, `ViewSortOrder`, system views |

### Tags

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`tags_example.py`](examples/tags_example.py) | Create and apply tags | `TagLookup`, boolean vs valued tags, `create_tag()`, `get_effective_tags()` |

### Search

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`search_example.py`](examples/search_example.py) | Search identifiers, cases, and entries | `search_identifiers()`, `search_cases()`, `query_journal_entries()`, filters |

### Automation Management

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`automation_management_example.py`](examples/automation_management_example.py) | Manage automation identities and API keys | `create_automation()`, `create_automation_api_key()`, key rotation |

### Reports

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`reports_example.py`](examples/reports_example.py) | Generate and download reports | `generate_identifier_report()`, `generate_view_report()`, `wait_for_report()`, PDF/CSV formats |

### Real-time Notifications

| Example | Description | Key Concepts |
|---------|-------------|--------------|
| [`websocket_notifications.py`](examples/websocket_notifications.py) | Listen for real-time notifications | `create_websocket_client()`, async handlers, `listen_notifications()` |
| [`websocket_custom_handlers.py`](examples/websocket_custom_handlers.py) | Custom WebSocket message handlers | Custom message types, error handling |

### Running Examples

```bash
# Set environment variables
export SCAMBUS_API_URL="http://localhost:8080/api"
export SCAMBUS_API_TOKEN="your-token"

# Run an example
python examples/simple_detection.py

# Run example with file argument
python examples/detection_with_evidence.py screenshot.png
```

---

## 11. Appendices

### Valid Identifier Types

| Type | Description | Example |
|------|-------------|---------|
| `phone` | Phone numbers (E.164) | +12125551234 |
| `email` | Email addresses | user@example.com |
| `url` | URLs/domains | https://scam-site.com |
| `bank_account` | Bank account info | Wells Fargo ****1234 |
| `crypto_wallet` | Crypto wallet addresses | BTC: 1A1z... |
| `social_media` | Social media handles | Instagram: @scammer |
| `payment_token` | Payment service IDs | Zelle: user@example.com |
| `zelle` | Zelle identifiers | user@example.com |

### Configuration File Format

`~/.scambus/config.json`:
```json
{
  "auth": {
    "type": "device",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "...",
    "expires_at": 1737244800.0
  }
}
```

### JSONPath Filter Expressions

Identifier messages support filtering on:
- `$.type` - Identifier type
- `$.confidence` - Confidence score (0.0-1.0)
- `$.details.*` - Any field in details object
- `$.display_value` - Normalized display value

Examples:
```
$.type == "phone"
$.type == "phone" || $.type == "email"
$.type == "phone" && $.confidence >= 0.9
$.details.platform == "whatsapp"
$.details.is_toll_free == true
```

---

## Support

- **Documentation**: https://scambus.github.io/scambus-python-client/
- **Issues**: https://github.com/scambus/python-client/issues
- **Discussions**: https://github.com/scambus/python-client/discussions
- **Security**: security@scambus.net

---

*Last updated: 2025-11-11 | Version: 0.1.0*
