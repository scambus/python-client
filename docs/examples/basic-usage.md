# Basic Usage Examples

Simple examples to get started with the Scambus Python client.

## Installation

```bash
pip install scambus-client
```

## Creating a Detection

```python
from scambus_client import ScambusClient

client = ScambusClient(
    api_url="https://api.scambus.net",
    api_token="your-api-token"
)

# Create a detection journal entry
entry = client.create_detection(
    description="Phishing email from fake bank",
    identifiers=["email:scammer@example.com"],
    category="phishing",
    confidence=0.95
)

print(f"Created entry: {entry.id}")
```

## Searching for Identifiers

```python
# Search for an identifier
results = client.search_identifiers(
    query="+1234567890",
    identifier_type="phone"
)

for identifier in results:
    print(f"{identifier.type}: {identifier.display_value}")
```

See [Advanced Examples](advanced.md) for more complex use cases.
