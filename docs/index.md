# Scambus Python Client

Official Python client for Scambus - submit scam reports and subscribe to data streams.

[![PyPI version](https://badge.fury.io/py/scambus-client.svg)](https://badge.fury.io/py/scambus-client)
[![Python Support](https://img.shields.io/pypi/pyversions/scambus-client.svg)](https://pypi.org/project/scambus-client/)
[![Tests](https://github.com/scambus/scambus-python-client/workflows/Tests/badge.svg)](https://github.com/scambus/scambus-python-client/actions)
[![codecov](https://codecov.io/gh/scambus/scambus-python-client/branch/main/graph/badge.svg)](https://codecov.io/gh/scambus/scambus-python-client)

## Overview

The Scambus Python Client provides a simple and intuitive interface for interacting with the Scambus API. It allows you to:

- **Submit scam reports**: Phone calls, emails, text messages, detections, and more
- **Search data**: Find identifiers, cases, and journal entries
- **Stream events**: Subscribe to real-time scam data with export streams
- **Manage cases**: Create and track investigation cases
- **Track activities**: Monitor ongoing scam interactions with in-progress activities

## Quick Example

```python
from scambus_client import ScambusClient
from datetime import datetime

# Initialize client
client = ScambusClient(
    base_url="https://api.scambus.net",
    api_key="your-api-key"
)

# Submit a scam detection
detection = client.create_detection(
    description="Phishing email pretending to be from bank",
    identifiers=["email:scammer@example.com"],
    category="phishing",
    confidence=0.9
)

# Create an in-progress phone call
call = client.create_phone_call(
    description="Suspicious tech support call",
    direction="inbound",
    start_time=datetime.now(),
    identifiers=["phone:+1234567890"],
    in_progress=True  # Call is still ongoing
)

# Later... complete the call
call.complete(description="Scammer hung up after being questioned")

# Create a stream to monitor new phone scams
stream = client.create_stream(
    name="Phone Scams Monitor",
    filters={"type": "phone_call"}
)

# Consume events from the stream
for event in client.consume_stream(stream.id, limit=10):
    print(f"New phone scam: {event}")
```

## Features

### Journal Entries (Scam Reports)
Submit different types of scam reports including detections, phone calls, emails, text conversations, and notes.

[Learn more →](user-guide/journal-entries.md)

### In-Progress Activities
Track ongoing scam interactions in real-time. Start activities without an end time and complete them later.

[Learn more →](user-guide/in-progress-activities.md)

### Export Streams
Subscribe to real-time scam data with filtered export streams. Consume events, recover from failures, and backfill historical data.

[Learn more →](user-guide/streams.md)

### Search
Search across identifiers, cases, and journal entries with flexible query options.

[Learn more →](user-guide/search.md)

### Case Management
Create and manage investigation cases, track progress, and collaborate with team members.

[Learn more →](user-guide/cases.md)

## Installation

Install the library:

```bash
pip install scambus-client
```

Install with CLI support:

```bash
pip install scambus-client[cli]
```

[Full installation guide →](getting-started/installation.md)

## CLI Usage

The package includes a command-line interface:

```bash
# Set up authentication
export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"

# Submit a detection
scambus journal create-detection \
    --description "Phishing website" \
    --identifier email:scammer@example.com \
    --category phishing \
    --confidence 0.9

# Create a data stream
scambus streams create \
    --name "High Confidence Detections" \
    --filter confidence=0.9

# Search for identifiers
scambus search identifiers --query "+1234567890"
```

[Full CLI reference →](cli-reference/overview.md)

## Next Steps

- [Quick Start Guide](getting-started/quickstart.md) - Get up and running quickly
- [API Reference](api-reference/client.md) - Complete API documentation
- [Examples](examples/basic-usage.md) - Code examples for common tasks
- [Contributing](development/contributing.md) - Learn how to contribute

## Support

- **Documentation**: [docs.scambus.net](https://docs.scambus.net)
- **Issues**: [GitHub Issues](https://github.com/scambus/scambus-python-client/issues)
- **Discussions**: [GitHub Discussions](https://github.com/scambus/scambus-python-client/discussions)
- **Security**: See [SECURITY.md](https://github.com/scambus/scambus-python-client/blob/main/SECURITY.md)

## License

TBD
