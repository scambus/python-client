# Stream Commands

Manage export streams.

## Commands

- `scambus streams create` - Create a new stream
- `scambus streams list` - List all streams
- `scambus streams consume` - Consume entries from a stream

## Examples

```bash
scambus streams create --name "Phone Scams" --filter type=phone_call
scambus streams consume --stream-id abc123
```
