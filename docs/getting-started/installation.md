# Installation

## Requirements

- Python 3.8 or higher
- pip package manager

## Install from PyPI

### Library Only

To install just the Python library:

```bash
pip install scambus-client
```

This installs the core library with minimal dependencies (only `requests`).

### Library + CLI

To install the library with CLI support:

```bash
pip install scambus-client[cli]
```

This includes additional dependencies:
- `click` - CLI framework
- `rich` - Rich terminal output
- `tabulate` - Table formatting

### Development Installation

For development, install with all development dependencies:

```bash
pip install scambus-client[dev]
```

This includes:
- All CLI dependencies
- Testing tools (pytest, pytest-cov)
- Code quality tools (black, ruff, isort, mypy)
- Pre-commit hooks
- Security scanners (bandit)

## Install from Source

To install from source (e.g., for development or testing):

```bash
# Clone the repository
git clone https://github.com/scambus/scambus-python-client.git
cd scambus-python-client

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Verify Installation

### Library

Verify the library is installed:

```python
import scambus_client
print(scambus_client.__version__)
```

### CLI

Verify the CLI is installed:

```bash
scambus --version
```

## Virtual Environments

We recommend using virtual environments to isolate dependencies:

### Using venv (built-in)

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install scambus-client
pip install scambus-client[cli]
```

### Using conda

```bash
# Create environment
conda create -n scambus python=3.11

# Activate
conda activate scambus

# Install scambus-client
pip install scambus-client[cli]
```

## Upgrading

To upgrade to the latest version:

```bash
pip install --upgrade scambus-client
```

To upgrade with CLI:

```bash
pip install --upgrade scambus-client[cli]
```

## Uninstalling

To uninstall:

```bash
pip uninstall scambus-client
```

## Troubleshooting

### ImportError: No module named 'scambus_client'

This means the package is not installed. Run:

```bash
pip install scambus-client
```

### Command not found: scambus

The CLI was not installed. Install with CLI support:

```bash
pip install scambus-client[cli]
```

### Permission denied

On Linux/macOS, you might need to use `--user`:

```bash
pip install --user scambus-client[cli]
```

Or use a virtual environment (recommended).

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with the library
- [Authentication](authentication.md) - Set up API credentials
