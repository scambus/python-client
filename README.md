# SCAMBUS Python Client

Official Python client for SCAMBUS - submit scam reports and subscribe to data streams.

> **💡 Quick Start:** Install directly from GitHub:
> ```bash
> pip install git+https://github.com/scambus/python-client.git
> ```

## Features

- **Submit Scam Reports**: Phone calls, emails, text messages, detections, and more
- **Search**: Find identifiers, cases, and journal entries
- **Data Streams**: Subscribe to real-time scam data with export streams
- **Real-time Notifications**: WebSocket support for instant notifications and updates
- **Case Management**: Create and manage investigation cases
- **Tagging**: Organize data with tags
- **Evidence**: Upload and attach media evidence
- **In-Progress Activities**: Track ongoing scam interactions

## Installation

### From PyPI (Recommended - when available)

```bash
pip install scambus
```

### From GitHub (Pre-release / Development)

Install directly from the GitHub repository:

```bash
# Install latest from main branch
pip install git+https://github.com/scambus/python-client.git

# Install specific version/tag
pip install git+https://github.com/scambus/python-client.git@v0.1.0

# Install specific branch
pip install git+https://github.com/scambus/python-client.git@feature-branch
```

📖 **See [INSTALL_FROM_GITHUB.md](INSTALL_FROM_GITHUB.md) for detailed instructions and troubleshooting.**

The package includes:
- Python client library (`scambus_client`)
- CLI tool (`scambus` command)

### Optional: Install Development Tools

```bash
# From PyPI
pip install scambus[dev]

# From GitHub
pip install "git+https://github.com/scambus/python-client.git#egg=scambus[dev]"
```

## Quick Start

### Library Usage

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

# Search for identifiers
results = client.search_identifiers(
    query="+1234567890",
    identifier_type="phone"
)
```

### Real-time Notifications (WebSocket)

```python
import asyncio
from scambus_client import ScambusClient

# Initialize client
client = ScambusClient(
    api_url="https://api.scambus.net/api",
    api_key_id="your-key-id",
    api_key_secret="your-secret"
)

# Create WebSocket client
ws_client = client.create_websocket_client()

# Define notification handler
async def handle_notification(notification):
    print(f"New notification: {notification['title']}")
    print(f"Message: {notification['message']}")

# Start listening for notifications
asyncio.run(ws_client.listen_notifications(handle_notification))
```

See `examples/websocket_notifications.py` and `examples/websocket_custom_handlers.py` for more advanced usage.

### CLI Usage

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

# Create an in-progress phone call
scambus journal create-phone-call \
    --description "Tech support scam call" \
    --direction inbound \
    --duration 0 \  # Will be calculated when completed
    --phone "+1234567890" \
    --platform pstn

# Upload evidence
scambus media upload screenshot.png \
    --notes "Screenshot of phishing site"

# Create a journal entry stream
scambus streams create \
    --name "High Confidence Detections" \
    --data-type journal_entry \
    --min-confidence 0.9

# Create an identifier stream with backfill
scambus streams create \
    --name "Phone State Changes" \
    --data-type identifier \
    --identifier-type phone \
    --min-confidence 0.8 \
    --backfill \
    --backfill-from-date 2025-01-01T00:00:00Z

# Consume from a stream
scambus streams consume <stream-id> --limit 100

# Recover a stream after Redis failure
scambus streams recover <stream-id>

# Trigger backfill for identifier stream
scambus streams backfill <stream-id> --from-date 2025-01-01T00:00:00Z

# Check recovery status
scambus streams recovery-status

# Get stream recovery info
scambus streams recovery-info <stream-id>

# Search for identifiers
scambus search identifiers --query "+1234567890"

# Search for cases
scambus search cases --query "phishing"

# Manage your profile
scambus profile notifications
scambus profile sessions
scambus profile passkeys
scambus profile twofa --enable
```

## Documentation

- [Quick Start Guide](docs/quickstart.md)
- [API Reference](docs/api-reference.md)
- [CLI Reference](docs/cli-reference.md)
- [Examples](examples/)

## Features in Detail

### Journal Entries (Scam Reports)

Submit different types of scam reports:

- **Detections**: Automated or manual scam detections
- **Phone Calls**: Scam phone calls
- **Emails**: Phishing or scam emails
- **Text Conversations**: SMS or messaging app scams
- **Notes**: General observations

### In-Progress Activities

Track ongoing scam interactions:

```python
# Start tracking an activity
call = client.create_phone_call(
    description="Ongoing scam call",
    direction="inbound",
    start_time=datetime.now(),
    in_progress=True  # No end_time
)

# Complete it later
call.complete(
    end_time=datetime.now(),
    completion_reason="manual",
    description="Call completed - scammer identified"
)
```

### Export Streams

Subscribe to real-time scam data with two types of streams:

#### Journal Entry Streams

Receive complete journal entries as they're created:

```python
# Create a journal entry stream
stream = client.create_stream(
    name="High-Confidence Phone Scams",
    data_type="journal_entry",  # Default
    identifier_types=["phone"],
    min_confidence=0.8,
    max_confidence=1.0
)

# Consume journal entries
result = client.consume_stream(stream.id, cursor="0", limit=10)
for msg in result['messages']:
    print(f"Journal Entry: {msg['type']}")
    print(f"Identifiers: {len(msg['identifiers'])}")
```

#### Identifier Streams

Track identifier state changes (confidence, tags, type):

```python
# Create an identifier stream
stream = client.create_stream(
    name="Phone Number State Changes",
    data_type="identifier",  # Track identifier changes
    identifier_types=["phone"],
    min_confidence=0.9,
    backfill_historical=True,  # Backfill existing identifiers
    backfill_from_date="2025-01-01T00:00:00Z"
)

# Consume identifier state changes
result = client.consume_stream(stream.id, cursor="0", limit=10)
for msg in result['messages']:
    print(f"Identifier: {msg['type']} - {msg['displayValue']}")
    print(f"Confidence: {msg['confidence']}")
    print(f"Triggered by: {msg['triggeringJournalEntry']['type']}")
```

#### Stream Management

```python
# Recover from Redis failures
client.recover_stream(stream.id, ignore_checkpoint=False, clear_stream=True)

# Backfill historical identifier data (identifier streams only)
client.backfill_stream(stream.id, from_date="2025-01-01T00:00:00Z")

# Check recovery status
status = client.get_recovery_status()
for log in status['logs']:
    print(f"{log['streamName']}: {log.get('completedAt', 'In Progress')}")

# Get stream recovery info
info = client.get_stream_recovery_info(stream.id)
print(f"Is Rebuilding: {info['isRebuilding']}")
```

#### Key Differences

| Feature | Journal Entry Stream | Identifier Stream |
|---------|---------------------|-------------------|
| Data Type | `journal_entry` | `identifier` |
| Publishes | Complete journal entries | Identifier state changes |
| Frequency | Every matching JE | Only on state change |
| Contains | JE + all identifiers + evidence | Identifier state + triggering JE |
| Backfill | Not supported | Supported |
| Use Case | Track all scam events | Track identifier evolution |

### Search

Search across identifiers and cases:

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

### Case Management

Create and manage investigation cases:

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
```

### Tags

Organize your data:

```python
# List available tags
tags = client.list_tags()

# Create a tag
tag = client.create_tag(
    name="High Priority",
    tag_type="priority"
)

# Tags are applied automatically by the backend based on rules
# and visibility is controlled server-side
```

## Authentication

The client supports API key authentication:

```python
client = ScambusClient(
    base_url="https://api.scambus.net",
    api_key="your-api-key"
)
```

Or via environment variables:

```bash
export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"
```

```python
import os
client = ScambusClient(
    base_url=os.getenv('SCAMBUS_URL'),
    api_key=os.getenv('SCAMBUS_API_KEY')
)
```

## Error Handling

```python
from scambus_client import (
    ScambusClient,
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusValidationError,
    ScambusNotFoundError
)

try:
    entry = client.create_detection(...)
except ScambusAuthenticationError:
    print("Invalid API key")
except ScambusValidationError as e:
    print(f"Validation error: {e}")
except ScambusNotFoundError:
    print("Resource not found")
except ScambusAPIError as e:
    print(f"API error: {e}")
```

## Examples

See the [examples/](examples/) directory for complete examples:

- [detection_with_evidence.py](examples/detection_with_evidence.py) - Submit a scam detection with evidence
- [phone_call_example.py](examples/phone_call_example.py) - Report a scam call
- [email_example.py](examples/email_example.py) - Report a phishing email
- [text_conversation_example.py](examples/text_conversation_example.py) - Report SMS/text scams
- [stream_management.py](examples/stream_management.py) - Manage export streams
- [identifier_stream_example.py](examples/identifier_stream_example.py) - **Identifier stream usage and backfill**
- [case_management.py](examples/case_management.py) - Manage investigation cases
- [simple_media_upload.py](examples/simple_media_upload.py) - Upload evidence files

## Development

### Prerequisites

- Python 3.8+
- Git
- Virtual environment (recommended)

### Setup Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/scambus/python-client.git
   cd scambus-python-client
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all unit tests
pytest tests/ -m "not integration"

# Run with coverage
pytest tests/ -m "not integration" --cov=scambus_client --cov=scambus_cli

# Run integration tests (requires test environment)
export SCAMBUS_TEST_URL="https://test-api.scambus.net"
export SCAMBUS_TEST_API_KEY="test-key"
pytest tests/integration/ -m integration
```

### Code Quality

```bash
# Format code
black scambus_client/ scambus_cli/ tests/
isort scambus_client/ scambus_cli/ tests/

# Run linters
ruff check scambus_client/ scambus_cli/ tests/
mypy scambus_client/ scambus_cli/

# Security checks
bandit -r scambus_client/ scambus_cli/

# Run all checks (automatically done by pre-commit)
pre-commit run --all-files
```

### Building Documentation

```bash
# Install documentation dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build
```

### Building Package

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check package
twine check dist/*
```

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat(client): add bulk journal entry creation
fix(streams): handle empty cursor in consume_stream
docs(readme): update installation instructions
test(models): add tests for in-progress activities
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

### Quick Contributing Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes using conventional commits
6. Push to your fork
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://scambus.github.io/scambus-python-client/](https://scambus.github.io/scambus-python-client/)
- **Issues**: [GitHub Issues](https://github.com/scambus/python-client/issues)
- **Discussions**: [GitHub Discussions](https://github.com/scambus/python-client/discussions)
- **Security**: See [SECURITY.md](SECURITY.md)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and breaking changes.

## Related Projects

- **scambus-python-admin** (Private) - Admin extension library for Scambus administrators
- **scambus-admin-cli** (Private) - Admin CLI with additional administrative commands

## Project Status

- ✅ Stable public API
- ✅ Comprehensive test coverage (>80%)
- ✅ Full documentation
- ✅ Active development
- ✅ Production ready

---

**Note**: This is the public client library focused on submitting scam reports and consuming data.
Administrative functions (user management, permissions, etc.) are available in the private `scambus-python-admin` package.
