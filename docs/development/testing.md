# Testing

Guidelines for testing the Scambus Python client.

## Running Tests

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/ -m "not integration"

# Run with coverage
pytest tests/ --cov=scambus_client --cov=scambus_cli
```

## Writing Tests

- Place unit tests in `tests/`
- Place integration tests in `tests/integration/`
- Mark integration tests with `@pytest.mark.integration`
- Use fixtures from `tests/conftest.py`

## Test Structure

```python
import pytest
from scambus_client import ScambusClient

def test_example(client):
    """Test description."""
    result = client.some_method()
    assert result is not None
```

See [Contributing](contributing.md) for development guidelines.
