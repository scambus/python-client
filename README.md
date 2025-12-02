# SCAMBUS Python Client

Official Python client for SCAMBUS - submit scam reports and subscribe to data streams.

> **💡 Quick Start:** Install directly from GitHub:
> ```bash
> pip install git+https://github.com/scambus/python-client.git
> ```

## Features

- **Submit Scam Reports**: Phone calls, emails, text messages, detections, and more
- **Tagging**: Apply boolean and valued tags when creating journal entries
- **Search**: Find identifiers, cases, and journal entries
- **Views (Saved Queries)**: Create, execute, and manage saved query views
- **In-Progress Activities**: Track and complete ongoing scam interactions
- **Data Streams**: Subscribe to real-time scam data with export streams (journal entries and identifier state changes)
- **Real-time Notifications**: WebSocket support for instant notifications and updates
- **Case Management**: Create and manage investigation cases
- **Evidence**: Upload and attach media evidence
- **Automation Management**: Create automation identities with API key rotation support
- **Automatic Authentication**: CLI and SDK share cached credentials seamlessly
- **Device Flow Auth**: Secure browser-based authentication with automatic token refresh

## Installation

### From GitHub 

Install directly from the GitHub repository:

```bash
# Install latest from main branch
pip install git+https://github.com/scambus/python-client.git

# Install specific version/tag
pip install git+https://github.com/scambus/python-client.git@v0.1.0

# Install specific branch
pip install git+https://github.com/scambus/python-client.git@feature-branch
```

📖 **See [DOCUMENTATION_SUMMARY.md](DOCUMENTATION_SUMMARY.md) for complete documentation.**

The package includes:
- Python client library (`scambus_client`)
- CLI tool (`scambus` command)

### Optional: Install Development Tools

```bash
# From GitHub
pip install "git+https://github.com/scambus/python-client.git#egg=scambus[dev]"
```

## Quick Start

### 1. Authentication

Authenticate using the CLI - credentials are automatically cached and shared with the SDK:

```bash
# Interactive login (opens browser)
scambus auth login

# Check status
scambus auth status
```

### 2. Submit Scam Reports (CLI)

```bash
# Report a phishing detection with tags
scambus journal create-detection \
    --description "Phishing email pretending to be from bank" \
    --identifier email:scammer@example.com \
    --tag "Phishing" \
    --tag "ScamType:Banking" \
    --confidence 0.9

# Report an ongoing scam call
scambus journal create-phone-call \
    --description "Tech support scam in progress" \
    --direction inbound \
    --phone "+1234567890" \
    --platform pstn

# View your in-progress activities
scambus journal in-progress

# Query your journal entries
scambus journal query --search "phishing" --limit 10

# View saved queries
scambus views list
scambus views my-journal
```

### 3. Use the Python SDK

The SDK automatically uses your CLI authentication and provides typed objects similar to AWS CDK:

```python
from scambus_client import ScambusClient, TagLookup, ViewFilter, ViewSortOrder
from datetime import datetime

# No credentials needed - auto-loads from CLI
client = ScambusClient()

# Submit a scam detection with typed tags
detection = client.create_detection(
    description="Phishing email pretending to be from bank",
    identifiers=["email:scammer@example.com"],
    confidence=0.9,
    tags=[
        TagLookup(tag_name="Phishing"),
        TagLookup(tag_name="ScamType", tag_value="Banking")
    ]
)

# Or use dictionaries for backward compatibility
detection = client.create_detection(
    description="Phishing email",
    identifiers=["email:scammer@example.com"],
    confidence=0.9,
    tags=[
        {"tag_name": "Phishing"},
        {"tag_name": "ScamType", "tag_value": "Banking"}
    ]
)

# Create an in-progress phone call
call = client.create_phone_call(
    description="Suspicious tech support call",
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

# Get in-progress activities
activities = client.get_in_progress_activities()

# Execute saved views
my_journal = client.execute_my_journal_entries(limit=20)
for entry in my_journal['data']:
    print(f"{entry['type']}: {entry['description']}")

# Create view with typed filters
view = client.create_view(
    name="High Confidence Detections",
    entity_type="journal",
    filter_criteria=ViewFilter(
        min_confidence=0.9,
        entry_types=["detection"]
    ),
    sort_order=ViewSortOrder(field="created_at", direction="desc")
)

# Search for identifiers
results = client.search_identifiers(
    query="+1234567890",
    identifier_type="phone"
)

# Create and consume export streams
stream = client.create_stream(
    name="Phone Scams Monitor",
    data_type="journal_entry",
    identifier_types=["phone"]
)

result = client.consume_stream(stream.id, cursor="0", limit=10)
for msg in result['messages']:
    print(f"New phone scam: {msg['type']}")
```

### 4. Automation Setup

Create dedicated automation accounts for scripts:

```bash
# Login as yourself first
scambus auth login

# Create an automation
scambus automations create --name "Phishing Detector Bot" \
    --description "Automated phishing detection"

# Create API key and switch to it
scambus automations create-key "Phishing Detector Bot" --assume
# ✓ API key created: key_abc123:secret_xyz789
# ✓ Now operating as automation

# Run your script (uses automation credentials automatically)
python my_detector.py

# Switch back to personal account
scambus auth login
```

### 5. Local Development

```python
# Override API URL for local development
client = ScambusClient(api_url="http://localhost:8080/api")
```

Or use environment variable:
```bash
export SCAMBUS_URL="http://localhost:8080"
scambus journal query --search "test"
```

### Real-time Notifications (WebSocket)

```python
import asyncio
from scambus_client import ScambusClient

# Initialize client - uses cached authentication
client = ScambusClient()

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
# First, authenticate
scambus auth login

# Submit a detection with tags
scambus journal create-detection \
    --description "Phishing website" \
    --identifier email:scammer@example.com \
    --tag "Phishing" \
    --tag "ScamType:Banking" \
    --confidence 0.9

# Create an in-progress phone call
scambus journal create-phone-call \
    --description "Tech support scam call" \
    --direction inbound \
    --phone "+1234567890" \
    --platform pstn \
    --tag "TechSupport"

# Upload evidence
scambus media upload screenshot.png \
    --notes "Screenshot of phishing site"

# Query journal entries
scambus journal query --search "phishing" --limit 20

# View in-progress activities
scambus journal in-progress

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

# Manage views (saved queries)
scambus views list
scambus views my-journal
scambus views execute <view-id>

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

- [Complete Documentation](DOCUMENTATION_SUMMARY.md) - Full reference guide
- [Examples](examples/) - Working code examples
- [Changelog](CHANGELOG.md) - Version history
- [Security](SECURITY.md) - Security policy

## Features in Detail

### Journal Entries (Scam Reports)

Submit different types of scam reports with tag support:

- **Detections**: Automated or manual scam detections
- **Phone Calls**: Scam phone calls
- **Emails**: Phishing or scam emails
- **Text Conversations**: SMS or messaging app scams
- **Notes**: General observations

All journal entry types support tagging during creation:

```bash
# CLI - Boolean tags
scambus journal create-detection \
    --description "Ransomware detected" \
    --tag "Malware" \
    --tag "HighPriority"

# CLI - Valued tags
scambus journal create-detection \
    --description "Phishing campaign" \
    --tag "ScamType:Phishing" \
    --tag "Industry:Banking"
```

```python
# SDK - Typed tags (recommended, AWS CDK-style)
from scambus_client import TagLookup

client.create_detection(
    description="Phishing campaign",
    identifiers=["email:scam@example.com"],
    tags=[
        TagLookup(tag_name="ScamType", tag_value="Phishing"),  # Valued tag
        TagLookup(tag_name="HighPriority")  # Boolean tag
    ]
)

# SDK - Dictionary tags (backward compatible)
client.create_detection(
    description="Phishing campaign",
    identifiers=["email:scam@example.com"],
    tags=[
        {"tag_name": "ScamType", "tag_value": "Phishing"},
        {"tag_name": "HighPriority"}
    ]
)
```

### In-Progress Activities

Track ongoing scam interactions:

```bash
# CLI - View in-progress activities
scambus journal in-progress
```

```python
# SDK - Create in-progress activity
call = client.create_phone_call(
    description="Ongoing scam call",
    direction="inbound",
    start_time=datetime.now(),
    in_progress=True  # No end_time
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

### Views (Saved Queries)

Create and execute saved query views for common searches:

```bash
# CLI - List available views
scambus views list

# Execute system views
scambus views my-journal
scambus views my-pinboard

# Get view details
scambus views get VIEW_ID

# Execute custom view
scambus views execute VIEW_ID --limit 20

# Create custom view
scambus views create \
    --name "High Confidence Phone Scams" \
    --entity-type journal \
    --filter-criteria '{"identifier_types": ["phone"], "min_confidence": 0.9}'
```

```python
# SDK - Execute views
my_entries = client.execute_my_journal_entries(limit=20)
pinned = client.execute_my_pinboard(limit=10)

# List and execute custom views
views = client.list_views()
result = client.execute_view(view_id, limit=20)

# Create custom view
view = client.create_view(
    name="High Confidence Detections",
    entity_type="journal",
    filter_criteria={"min_confidence": 0.9},
    visibility="organization"
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

### Automation Management

Create and manage automation identities with API key support:

```bash
# List automations
scambus automations list

# Create an automation
scambus automations create --name "My Bot" --description "Automated detection"

# Create API key (by name or UUID)
scambus automations create-key "My Bot" --name "Production Key"
scambus automations create-key abc-123-def-456 --name "Dev Key"

# Create API key and immediately switch to it
scambus automations create-key "My Bot" --assume

# List API keys for an automation
scambus automations list-keys abc-123-def-456

# Revoke an API key
scambus automations revoke-key abc-123 key-456

# Delete an API key
scambus automations delete-key abc-123 key-456
```

**Note on ambiguous names**: If multiple automations share the same name, `create-key` will display all matches and require you to use the UUID instead:

```bash
$ scambus automations create-key "My Bot" --assume
✗ Multiple automations found with name: My Bot

Ambiguous automation name. Please use UUID instead:

┌─ Matching Automations ──────────────────────────┐
│ ID          Name     Created    │
├─────────────────────────────────────────────────┤
│ abc-123-... My Bot   2025-01-15 │
│ def-456-... My Bot   2025-01-20 │
└─────────────────────────────────────────────────┘

Example: scambus automations create-key <UUID> --name "Key Name"
```

```python
# SDK - Create automation
automation = client.create_automation(
    name="Phishing Detector",
    description="Automated phishing detection bot"
)

# Create API key for automation
key_data = client.create_automation_api_key(
    automation_id=automation["id"],
    name="Production Key"
)
api_key = f"{key_data['accessKeyId']}:{key_data['secretAccessKey']}"

# List automations
automations = client.list_automations()

# Manage API keys
keys = client.list_automation_api_keys(automation["id"])
client.revoke_automation_api_key(automation["id"], key_id)
client.delete_automation_api_key(automation["id"], key_id)
```

**Key rotation workflow:**
1. Create new key: `scambus automations create-key "Bot Name" --name "New Key"`
2. Update your scripts with the new key
3. Test the new key
4. Revoke old key: `scambus automations revoke-key AUTOMATION_ID OLD_KEY_ID`

## Authentication

The Scambus Python client supports two authentication methods, with automatic credential caching shared between CLI and SDK.

### Configuration Storage

Authentication credentials are stored at:
- **Location**: `~/.scambus/config.json`
- **Permissions**: `0o600` (read/write for owner only)
- **Shared**: Automatically used by both CLI and SDK

### Method 1: Device Authorization Flow (Recommended)

Best for interactive CLI usage and personal accounts. Uses OAuth 2.0 Device Authorization Grant.

```bash
# Start interactive login (opens browser)
scambus auth login
```

**How it works:**
1. CLI displays a verification URL and user code
2. You open the URL in your browser and enter the code
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

### Method 2: API Key Authentication

Best for automation, CI/CD pipelines, and programmatic access.

```bash
# Login with API key (obtain from web UI first)
scambus auth login --api-key "your-api-key-from-web-ui"
```

**How it works:**
1. Obtain API key from the Scambus web UI
2. Authenticate via CLI using `--api-key`
3. Server validates key and returns JWT token
4. Credentials are cached at `~/.scambus/config.json`

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

Override config file settings:

```bash
export SCAMBUS_URL="https://scambus.net"
export SCAMBUS_API_TOKEN="your-jwt-token"
```

```python
# SDK will use environment variables if set
client = ScambusClient()
```

### Authentication Management

```bash
# Check authentication status
scambus auth status

# Logout (removes cached credentials)
scambus auth logout

# Switch authentication methods
scambus auth login                                  # Switch to device flow
scambus auth login --api-key "different-api-key"    # Switch to different API key
```

### Example Workflows

#### Creating New Automation

```bash
# 1. Login as yourself
scambus auth login

# 2. Create an automation
scambus automations create --name "Phishing Detector" \
    --description "Automated phishing detection bot"
# ✓ Automation created: abc-123-def-456

# 3. Create API key and switch to it
scambus automations create-key "Phishing Detector" --assume
# ✓ API key created
# ⚠ Save this API key - it won't be shown again:
# key_abc123:secret_xyz789
# Switching to automation identity...
# ✓ Now operating as automation: Phishing Detector

# 4. Run automated tasks (SDK uses cached automation credentials)
python my_phishing_detector.py

# 5. Switch back to personal account
scambus auth login
```

#### Rotating API Keys

```bash
# 1. Login as yourself
scambus auth login

# 2. Create new key for existing automation (by name or UUID)
scambus automations create-key "Phishing Detector" --name "Rotated Key"
# ✓ API key created
# ⚠ Save this API key: key_new123:secret_new789

# 3. Update your scripts with the new key

# 4. Test the new key

# 5. Revoke the old key
scambus automations list-keys abc-123-def-456
scambus automations revoke-key abc-123-def-456 old-key-id
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
