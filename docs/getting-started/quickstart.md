# Quick Start

This guide will help you get started with the Scambus Python Client in just a few minutes.

## Installation

First, install the package:

```bash
pip install scambus-client[cli]
```

## Authentication

Set up your API credentials using environment variables:

```bash
export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"
```

[More on authentication →](authentication.md)

## Basic Usage

### Initialize the Client

```python
from scambus_client import ScambusClient

client = ScambusClient(
    base_url="https://api.scambus.net",
    api_key="your-api-key"
)
```

### Submit a Scam Report

```python
# Report a phishing detection
detection = client.create_detection(
    description="Phishing email pretending to be from bank",
    identifiers=["email:scammer@example.com"],
    category="phishing",
    confidence=0.9
)
print(f"Created detection: {detection.id}")
```

### Track an Ongoing Activity

```python
from datetime import datetime

# Start tracking a phone call that's still ongoing
call = client.create_phone_call(
    description="Tech support scam call in progress",
    direction="inbound",
    start_time=datetime.now(),
    identifiers=["phone:+1234567890"],
    in_progress=True  # No end_time yet
)

# Later, when the call ends...
completed_call = call.complete(
    description="Scammer hung up after being questioned"
)
```

### Search for Identifiers

```python
# Search for an email address
results = client.search_identifiers(
    query="scammer@example.com",
    identifier_type="email"
)

for identifier in results:
    print(f"Found: {identifier.value} (confidence: {identifier.confidence})")
```

### Subscribe to Data Streams

```python
# Create a stream for phone scams
stream = client.create_stream(
    name="Phone Scams Monitor",
    filters={"type": "phone_call", "confidence": 0.8}
)

# Consume events from the stream
events = client.consume_stream(stream.id, limit=100)
for event in events:
    print(f"New phone scam: {event.description}")
```

### Manage Cases

```python
# Create an investigation case
case = client.create_case(
    title="Phishing Campaign Investigation",
    description="Investigating coordinated phishing targeting bank customers",
    status="open"
)

# Add a comment
client.create_case_comment(
    case.id,
    comment="Found 15 related identifiers"
)

# Update status
client.update_case(case.id, status="in_progress")
```

## CLI Usage

The same operations can be performed using the CLI:

```bash
# Submit a detection
scambus journal create-detection \
    --description "Phishing email" \
    --identifier email:scammer@example.com \
    --category phishing \
    --confidence 0.9

# Track an in-progress phone call
scambus journal create-phone-call \
    --description "Tech support scam" \
    --direction inbound \
    --phone "+1234567890" \
    --in-progress

# Search
scambus search identifiers --query "scammer@example.com"

# Create stream
scambus streams create \
    --name "Phone Scams" \
    --filter type=phone_call

# Consume from stream
scambus streams consume <stream-id> --limit 100
```

## Error Handling

Always handle errors appropriately:

```python
from scambus_client import (
    ScambusClient,
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusValidationError,
    ScambusNotFoundError
)

try:
    entry = client.create_detection(
        description="Test detection",
        identifiers=["email:test@example.com"]
    )
except ScambusAuthenticationError:
    print("Invalid API key")
except ScambusValidationError as e:
    print(f"Validation error: {e}")
except ScambusNotFoundError:
    print("Resource not found")
except ScambusAPIError as e:
    print(f"API error: {e}")
```

## Next Steps

- [User Guide](../user-guide/journal-entries.md) - Learn about all features
- [API Reference](../api-reference/client.md) - Complete API documentation
- [Examples](../examples/basic-usage.md) - More code examples
- [CLI Reference](../cli-reference/overview.md) - Full CLI documentation
