# Advanced Examples

Advanced usage patterns and integrations.

## Working with Export Streams

```python
from scambus_client import ScambusClient

client = ScambusClient(api_url="...", api_token="...")

# Create a stream
stream = client.create_stream(
    name="High Priority Phone Scams",
    filters={"type": "phone_call", "confidence_min": 0.8}
)

# Consume entries
cursor = stream.cursor
while True:
    entries, new_cursor = client.consume_stream(stream.id, cursor)
    for entry in entries:
        process_entry(entry)
    cursor = new_cursor
    time.sleep(60)  # Poll every minute
```

## Batch Operations

```python
# Create multiple detections
identifiers = [
    "email:scam1@example.com",
    "email:scam2@example.com",
    "email:scam3@example.com"
]

for identifier in identifiers:
    client.create_detection(
        description=f"Scam from {identifier}",
        identifiers=[identifier],
        category="phishing"
    )
```

See the [examples directory](https://github.com/scambus/python-client/tree/main/examples) for complete working examples.
