# Identifier Structured Data Reference

When consuming identifier streams, each message includes a `details` field containing type-specific structured data. This document describes the available fields for each identifier type.

## Overview

All identifier stream messages have this basic structure:

```json
{
  "identifier_id": "uuid",
  "type": "phone|email|bank_account|crypto_wallet|social_media|zelle",
  "display_value": "normalized display value",
  "confidence": 0.0-1.0,
  "details": { ... },  // ← Type-specific structured data
  "tags": [...],
  "triggering_journal_entry": {...}
}
```

The `details` field contains structured, parsed data specific to each identifier type.

## Phone Numbers

**Type**: `phone`

**Display Value**: E.164 format (e.g., `+12345678901`)

**Structured Data Fields**:

```json
{
  "country_code": "+1",           // International dialing code
  "number": "2345678901",         // National number (without country code)
  "area_code": "234",             // Area code / NDC (optional)
  "is_toll_free": false,          // true if toll-free number
  "region": "US"                  // ISO region code (optional)
}
```

**Example Usage**:

```python
details = msg.get("details", {})
country_code = details.get('country_code') or details.get('countryCode')
area_code = details.get('area_code') or details.get('areaCode')
is_toll_free = details.get('is_toll_free', details.get('isTollFree', False))
region = details.get('region')

# Build a blocklist key by area code
if country_code == "+1" and area_code:
    blocklist_key = f"US-{area_code}"

# Detect toll-free scams
if is_toll_free and confidence > 0.9:
    add_to_toll_free_scam_list(msg['displayValue'])
```

**Parsing Details**:
- Uses libphonenumber library for robust international phone number parsing
- `area_code` extraction works for NANP (North American Numbering Plan) and many international formats
- `is_toll_free` detected via libphonenumber's number type classification
- `region` is the ISO country code (e.g., "US", "CA", "GB")

## Email Addresses

**Type**: `email`

**Display Value**: Normalized email address (lowercase)

**Structured Data Fields**:

```json
{
  "email": "user@example.com"     // Normalized email (lowercase)
}
```

**Example Usage**:

```python
details = msg.get("details", {})
email = details.get('email')

# Extract domain for domain-based filtering
domain = email.split('@')[1] if '@' in email else None
if domain in ['suspicious-domain.com', 'known-scammer.net']:
    block_sender(email)
```

**Note**: Future enhancement planned to include `domain` field for easier filtering.

## Bank Accounts

**Type**: `bank_account`

**Display Value**: Formatted account identifier

**Structured Data Fields**:

```json
{
  "account_number": "1234567890",   // Account number
  "routing": "021000021",           // Routing number
  "institution": "Example Bank",    // Bank name (optional)
  "owner": "John Doe",              // Account owner (optional)
  "owner_address": "123 Main St",   // Owner address (optional)
  "country": "US",                  // Country code (optional)
  "routing_bank": "Federal Reserve", // Routing bank name (optional)
  "account_type": "checking"        // Account type (optional)
}
```

**Example Usage**:

```python
details = msg.get("details", {})
routing = details.get('routing')
account_number = details.get('account_number') or details.get('accountNumber')

# Check against known fraudulent routing numbers
if routing in known_fraud_routing_numbers:
    flag_as_fraud(msg['identifier_id'])

# Build unique identifier
bank_key = f"{routing}:{account_number}"
```

## Cryptocurrency Wallets

**Type**: `crypto_wallet`

**Display Value**: Wallet address

**Structured Data Fields**:

```json
{
  "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  // Wallet address
  "currency": "BTC",                                // Currency code (optional)
  "network": "mainnet"                              // Network type (optional)
}
```

**Example Usage**:

```python
details = msg.get("details", {})
address = details.get('address')
currency = details.get('currency')
network = details.get('network')

# Route to currency-specific fraud databases
if currency == 'BTC':
    check_bitcoin_scam_database(address)
elif currency == 'ETH':
    check_ethereum_scam_database(address)
```

## Social Media Handles

**Type**: `social_media`

**Display Value**: Platform-prefixed handle (e.g., `@twitter:username`)

**Structured Data Fields**:

```json
{
  "platform": "twitter",     // Social media platform
  "handle": "username"       // Username/handle (without @)
}
```

**Example Usage**:

```python
details = msg.get("details", {})
platform = details.get('platform')
handle = details.get('handle')

# Build platform-specific URL
if platform == 'twitter':
    url = f"https://twitter.com/{handle}"
elif platform == 'instagram':
    url = f"https://instagram.com/{handle}"
elif platform == 'telegram':
    url = f"https://t.me/{handle}"
```

## Zelle Identifiers

**Type**: `zelle`

**Display Value**: Zelle payment identifier

**Structured Data Fields**:

```json
{
  "type": "email|phone",    // Type of Zelle identifier
  "value": "user@example.com | +12345678901"  // The identifier value
}
```

**Example Usage**:

```python
details = msg.get("details", {})
zelle_type = details.get('type')
zelle_value = details.get('value')

# Route to appropriate validation
if zelle_type == 'email':
    validate_email_format(zelle_value)
elif zelle_type == 'phone':
    validate_phone_format(zelle_value)
```

## Field Name Formats

The system may return field names in either **snake_case** or **camelCase** depending on the API endpoint. Always check for both when accessing structured data:

```python
# Handle both formats
country_code = details.get('country_code') or details.get('countryCode')
area_code = details.get('area_code') or details.get('areaCode')
is_toll_free = details.get('is_toll_free', details.get('isTollFree', False))
```

## Practical Examples

### Example 1: Building a Phone Number Blocklist

```python
def process_phone_identifier(msg):
    details = msg.get("details", {})
    display_value = msg.get('displayValue')
    confidence = msg.get('confidence')

    # Extract structured data
    country_code = details.get('country_code') or details.get('countryCode')
    area_code = details.get('area_code') or details.get('areaCode')
    is_toll_free = details.get('is_toll_free', details.get('isTollFree', False))

    # Decision logic based on structured data
    if confidence > 0.9:
        if is_toll_free:
            add_to_blocklist(display_value, category="toll_free_scam")
        elif country_code == "+1" and area_code in high_fraud_area_codes:
            add_to_blocklist(display_value, category="high_risk_area_code")
        elif country_code != "+1":
            add_to_blocklist(display_value, category="international_scam")
```

### Example 2: Cryptocurrency Scam Tracking

```python
def process_crypto_identifier(msg):
    details = msg.get("details", {})
    address = details.get('address')
    currency = details.get('currency')

    # Route to currency-specific services
    scam_db = get_scam_database(currency)
    scam_db.add_address(address, confidence=msg.get('confidence'))

    # Send to blockchain analysis
    if currency in ['BTC', 'ETH']:
        blockchain_analyzer.analyze_address(address, currency)
```

### Example 3: Multi-Platform Social Media Monitoring

```python
def process_social_media_identifier(msg):
    details = msg.get("details", {})
    platform = details.get('platform')
    handle = details.get('handle')

    # Build monitoring rules per platform
    monitoring_rules = {
        'twitter': lambda h: monitor_twitter_account(h),
        'telegram': lambda h: monitor_telegram_channel(h),
        'instagram': lambda h: monitor_instagram_account(h),
    }

    handler = monitoring_rules.get(platform)
    if handler:
        handler(handle)
```

## Data Validation and Parsing

All identifier structured data is:

1. **Validated on creation** - Uses libraries like libphonenumber for phones
2. **Normalized** - Display values are in standard formats (E.164 for phones, lowercase for emails)
3. **Immutable** - The `data` field doesn't change unless the identifier is recreated
4. **Type-specific** - Each identifier type has its own schema

## Schema Definitions

For the complete Go struct definitions, see:
- Backend: `/backend/internal/models/identifier_data.go`
- Frontend: TypeScript type definitions in `/frontend/src/types/`

## Related Documentation

- [Identifier Stream Example](examples/identifier_stream_example.py) - Complete working examples
- [Export Streams Documentation](README.md#export-streams) - Stream creation and consumption
- [API Reference](docs/api-reference.md) - Full API documentation
