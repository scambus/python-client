# Contributing

Contributions to the Scambus Python client are welcome!

## Development Setup

```bash
git clone https://github.com/scambus/python-client
cd python-client
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/
```

## Code Quality

We use:
- **black** for code formatting
- **ruff** for linting
- **mypy** for type checking
- **isort** for import sorting

Run all checks:

```bash
black scambus_client/ scambus_cli/ tests/
isort scambus_client/ scambus_cli/ tests/
ruff check scambus_client/ scambus_cli/ tests/
mypy scambus_client/ scambus_cli/
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

See [Testing](testing.md) for test guidelines.
