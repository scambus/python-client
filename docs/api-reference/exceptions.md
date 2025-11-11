# Exceptions

Exception classes raised by the Scambus client.

## Exception Hierarchy

All exceptions inherit from `ScambusAPIError`.

## Exception Classes

- `ScambusAPIError` - Base exception for all API errors
- `ScambusAuthenticationError` - Authentication failed (401)
- `ScambusValidationError` - Request validation failed (400, 422)
- `ScambusNotFoundError` - Resource not found (404)
- `ScambusServerError` - Server error (500+)

## Usage

```python
from scambus_client import ScambusClient, ScambusAuthenticationError

try:
    client = ScambusClient(api_url="...", api_token="invalid")
    client.create_detection(...)
except ScambusAuthenticationError:
    print("Invalid API token")
```
