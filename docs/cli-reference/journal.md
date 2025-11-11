# Journal Commands

Manage journal entries from the command line.

## Commands

- `scambus journal create-detection` - Create a detection entry
- `scambus journal create-phone-call` - Create a phone call entry  
- `scambus journal create-email` - Create an email entry
- `scambus journal list` - List journal entries

## Examples

```bash
scambus journal create-detection \
    --description "Phishing email detected" \
    --identifier email:scammer@example.com
```
