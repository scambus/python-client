# ScambusClient API Reference

Complete API reference for the `ScambusClient` class.

## Class: ScambusClient

The main client class for interacting with the Scambus API.

### Initialization

```python
from scambus_client import ScambusClient

client = ScambusClient(
    api_url="https://api.scambus.net",
    api_token="your-api-token"
)
```

### Methods

For detailed method documentation, see the inline docstrings in `scambus_client/client.py`.

### Journal Entry Methods

- `create_detection()` - Create a detection journal entry
- `create_phone_call()` - Create a phone call journal entry
- `create_email()` - Create an email journal entry
- `create_in_progress_activity()` - Create an in-progress activity
- `complete_activity()` - Complete an in-progress activity

### Search Methods

- `search_identifiers()` - Search for identifiers
- `search_cases()` - Search for cases

### Stream Methods

- `create_stream()` - Create an export stream
- `list_streams()` - List all streams
- `consume_stream()` - Consume entries from a stream

See [Models](models.md) for data model documentation.
