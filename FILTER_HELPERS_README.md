# Export Stream Filter Helpers

Helper functions to make it easy to filter export streams by identifier type without writing JSONPath expressions manually.

## Overview

The Scambus backend uses JSONPath filter expressions to filter identifiers in export streams. While powerful, JSONPath can be complex for simple use cases like filtering by identifier type.

These helper functions provide a simple, Pythonic interface for the most common filtering scenarios.

## Helper Functions

### `build_identifier_type_filter(identifier_types)`

Build a JSONPath filter expression for filtering by identifier type(s).

**Parameters:**
- `identifier_types`: Single identifier type (string) or list of types
  - Valid types: `phone`, `email`, `url`, `bank_account`, `crypto_wallet`, `social_media`, `payment_token`

**Returns:**
- JSONPath filter expression string

**Examples:**

```python
from scambus_client import build_identifier_type_filter

# Single type
filter_expr = build_identifier_type_filter("phone")
# Result: '$.type == "phone"'

# Multiple types
filter_expr = build_identifier_type_filter(["phone", "email"])
# Result: '$.type == "phone" || $.type == "email"'

# Financial identifiers
filter_expr = build_identifier_type_filter(["bank_account", "crypto_wallet"])
# Result: '$.type == "bank_account" || $.type == "crypto_wallet"'
```

### `build_combined_filter(identifier_types=None, min_confidence=None, max_confidence=None, custom_expression=None)`

Build a complex JSONPath filter expression combining multiple conditions.

**Parameters:**
- `identifier_types`: Single type or list of types to filter by (optional)
- `min_confidence`: Minimum confidence score, 0.0 to 1.0 (optional)
- `max_confidence`: Maximum confidence score, 0.0 to 1.0 (optional)
- `custom_expression`: Additional custom JSONPath expression to AND with other conditions (optional)

**Returns:**
- Combined JSONPath filter expression, or `None` if no conditions specified

**Examples:**

```python
from scambus_client import build_combined_filter

# Type + minimum confidence
filter_expr = build_combined_filter(
    identifier_types="phone",
    min_confidence=0.8
)
# Result: '$.type == "phone" && $.confidence >= 0.8'

# Multiple types + confidence range
filter_expr = build_combined_filter(
    identifier_types=["phone", "email"],
    min_confidence=0.9,
    max_confidence=1.0
)
# Result: '($.type == "phone" || $.type == "email") && $.confidence >= 0.9 && $.confidence <= 1.0'

# Type + custom filter
filter_expr = build_combined_filter(
    identifier_types="social_media",
    min_confidence=0.85,
    custom_expression='$.details.platform == "whatsapp"'
)
# Result: '$.type == "social_media" && $.confidence >= 0.85 && $.details.platform == "whatsapp"'
```

## Using with `create_stream()`

The `create_stream()` method now accepts an `identifier_types` parameter that automatically converts to a filter_expression.

### Simple Usage (Recommended)

```python
from scambus_client import ScambusClient

client = ScambusClient(api_url="...", api_token="...")

# Filter by single identifier type
stream = client.create_stream(
    name="Phone Numbers Only",
    data_type="identifier",
    identifier_types="phone",  # Automatically converted to filter_expression
    min_confidence=0.8
)

# Filter by multiple identifier types
stream = client.create_stream(
    name="Contact Info",
    data_type="identifier",
    identifier_types=["phone", "email"],  # Multiple types
    min_confidence=0.9
)

# Combine type filter with custom expression
stream = client.create_stream(
    name="WhatsApp Only",
    data_type="identifier",
    identifier_types="social_media",
    filter_expression='$.details.platform == "whatsapp"',  # Combined with type filter
    min_confidence=0.85
)
```

### Advanced Usage (Using Helpers Directly)

For more control, use the helper functions to build expressions manually:

```python
from scambus_client import ScambusClient, build_combined_filter

client = ScambusClient(api_url="...", api_token="...")

# Build complex filter
filter_expr = build_combined_filter(
    identifier_types=["phone", "email", "url"],
    min_confidence=0.9,
    custom_expression='$.details.verified == true'
)

# Use the pre-built expression
stream = client.create_stream(
    name="High Confidence Verified Contacts",
    data_type="identifier",
    filter_expression=filter_expr,
    min_confidence=0.9
)
```

## Common Use Cases

### Contact Information Streams

```python
# All contact info (phone + email)
stream = client.create_stream(
    name="Contact Info",
    data_type="identifier",
    identifier_types=["phone", "email"],
    min_confidence=0.8
)

# High confidence contacts only
stream = client.create_stream(
    name="High Confidence Contacts",
    data_type="identifier",
    identifier_types=["phone", "email"],
    min_confidence=0.95
)
```

### Financial Information Streams

```python
# Bank accounts and crypto wallets
stream = client.create_stream(
    name="Financial Identifiers",
    data_type="identifier",
    identifier_types=["bank_account", "crypto_wallet"],
    min_confidence=0.9
)

# Payment tokens (Zelle, CashApp, PayPal, etc.)
stream = client.create_stream(
    name="Payment Tokens",
    data_type="identifier",
    identifier_types="payment_token",
    min_confidence=0.85
)
```

### Social Media Streams

```python
# All social media
stream = client.create_stream(
    name="Social Media",
    data_type="identifier",
    identifier_types="social_media",
    min_confidence=0.7
)

# Specific platform (WhatsApp)
stream = client.create_stream(
    name="WhatsApp Only",
    data_type="identifier",
    identifier_types="social_media",
    filter_expression='$.details.platform == "whatsapp"',
    min_confidence=0.8
)
```

### Suspicious URLs

```python
# All URLs
stream = client.create_stream(
    name="Suspicious URLs",
    data_type="identifier",
    identifier_types="url",
    min_confidence=0.8
)

# Specific domain patterns (using custom filter)
stream = client.create_stream(
    name="Phishing Sites",
    data_type="identifier",
    identifier_types="url",
    filter_expression='$.details.url LIKE "%paypal%" OR $.details.url LIKE "%bank%"',
    min_confidence=0.9
)
```

## Valid Identifier Types

| Type | Description | Example |
|------|-------------|---------|
| `phone` | Phone numbers (E.164 format) | +12125551234 |
| `email` | Email addresses | user@example.com |
| `url` | URLs/domains | https://scam-site.com |
| `bank_account` | Bank account information | Wells Fargo ****1234 |
| `crypto_wallet` | Cryptocurrency wallet addresses | BTC: 1A1z... |
| `social_media` | Social media handles | Instagram: @scammer |
| `payment_token` | Payment service identifiers | Zelle: user@example.com |

## Error Handling

The helper functions validate input and raise `ValueError` for invalid parameters:

```python
# Invalid identifier type
try:
    build_identifier_type_filter("invalid_type")
except ValueError as e:
    print(e)  # "Invalid identifier type: invalid_type. Valid types are: ..."

# Invalid confidence range
try:
    build_combined_filter(min_confidence=1.5)
except ValueError as e:
    print(e)  # "min_confidence must be between 0 and 1"

# Empty identifier types
try:
    build_identifier_type_filter([])
except ValueError as e:
    print(e)  # "identifier_types cannot be empty"
```

## How It Works

### Behind the Scenes

When you use `identifier_types` in `create_stream()`, it:

1. Validates the identifier type(s) against the list of valid types
2. Builds a JSONPath expression using `build_identifier_type_filter()`
3. Combines with any custom `filter_expression` using AND logic
4. Sends the combined expression to the backend as `filter_expression`

**Example:**

```python
# You write:
stream = client.create_stream(
    name="Contact Info",
    identifier_types=["phone", "email"],
    filter_expression='$.confidence >= 0.9'
)

# Client sends to backend:
{
    "name": "Contact Info",
    "filter_expression": '($.type == "phone" || $.type == "email") && ($.confidence >= 0.9)'
}
```

### JSONPath Expressions

The backend evaluates filter expressions against identifier messages, which have this structure:

```json
{
  "type": "phone",
  "display_value": "+12125551234",
  "confidence": 0.95,
  "details": {
    "country_code": "+1",
    "number": "2125551234",
    "area_code": "212",
    "is_toll_free": false
  }
}
```

You can filter on:
- `$.type` - Identifier type
- `$.confidence` - Confidence score
- `$.details.*` - Any field in the details object
- `$.display_value` - Normalized display value

## Migration from Manual filter_expression

If you're currently using `filter_expression` directly, you can migrate to the simpler `identifier_types` parameter:

**Before:**
```python
stream = client.create_stream(
    name="Phone Numbers",
    filter_expression='$.type == "phone"'
)
```

**After:**
```python
stream = client.create_stream(
    name="Phone Numbers",
    identifier_types="phone"
)
```

**Before:**
```python
stream = client.create_stream(
    name="Contact Info",
    filter_expression='$.type == "phone" || $.type == "email"'
)
```

**After:**
```python
stream = client.create_stream(
    name="Contact Info",
    identifier_types=["phone", "email"]
)
```

## Testing

Run the provided test script to verify the helpers work correctly:

```bash
cd /path/to/scambus/python-client
python3 test_filter_helpers.py
```

To test with a live backend:

```bash
export SCAMBUS_URL="http://localhost:8080/api"
python3 test_stream_with_helper.py
```

## See Also

- [E2E Stream Tests Documentation](../tests/E2E_STREAM_TESTS_README.md)
- [Bugs Found During E2E Testing](../tests/BUGS_FOUND_E2E_TESTING.md)
- [Scambus Python Client API Documentation](https://docs.scambus.com/python-client)
