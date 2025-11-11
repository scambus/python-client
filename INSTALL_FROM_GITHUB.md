# Installing SCAMBUS Python Client from GitHub

This guide explains how to install the SCAMBUS Python client directly from GitHub before it's available on PyPI.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- git (for GitHub installation)

## Installation Methods

### Method 1: Direct Installation (Recommended)

Install the latest version from the main branch:

```bash
pip install git+https://github.com/scambus/scambus-python-client.git
```

This command:
- Downloads the latest code from GitHub
- Builds and installs the package
- Installs all dependencies
- Makes the `scambus` CLI command available

### Method 2: Install Specific Version/Tag

Install a specific release version:

```bash
# Install version 0.1.0
pip install git+https://github.com/scambus/scambus-python-client.git@v0.1.0
```

### Method 3: Install from Specific Branch

Install from a feature branch:

```bash
# Install from a feature branch
pip install git+https://github.com/scambus/scambus-python-client.git@feature-branch-name
```

### Method 4: Clone and Install (For Development)

If you want to contribute or modify the code:

```bash
# Clone the repository
git clone https://github.com/scambus/scambus-python-client.git
cd scambus-python-client

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

## Installation with Extras

### Development Tools

Install with development dependencies (testing, linting, etc.):

```bash
pip install "git+https://github.com/scambus/scambus-python-client.git#egg=scambus[dev]"
```

## Verify Installation

After installation, verify everything works:

```bash
# Test Python import
python -c "from scambus_client import ScambusClient; print('✅ Import successful')"

# Test CLI command
scambus --help

# Check version
python -c "import scambus_client; print(scambus_client.__version__)"
```

## Upgrading

To upgrade to the latest version from GitHub:

```bash
# Upgrade to latest main branch
pip install --upgrade git+https://github.com/scambus/scambus-python-client.git

# Force reinstall if needed
pip install --force-reinstall git+https://github.com/scambus/scambus-python-client.git
```

## Uninstalling

To uninstall:

```bash
pip uninstall scambus
```

## Troubleshooting

### Issue: "git: command not found"

**Solution:** Install git first:

```bash
# macOS (with Homebrew)
brew install git

# Ubuntu/Debian
sudo apt-get install git

# Windows
# Download from https://git-scm.com/download/win
```

### Issue: CLI command not found

**Solution:** Ensure pip's bin directory is in your PATH:

```bash
# Check where pip installs scripts
python -m site --user-base

# Add to PATH (example for bash)
export PATH="$PATH:$(python -m site --user-base)/bin"

# Or reinstall
pip install --force-reinstall git+https://github.com/scambus/scambus-python-client.git
```

### Issue: Permission denied

**Solution:** Use `--user` flag or virtual environment:

```bash
# Install for current user only
pip install --user git+https://github.com/scambus/scambus-python-client.git

# Or use virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install git+https://github.com/scambus/scambus-python-client.git
```

### Issue: Build fails

**Solution:** Ensure you have build tools installed:

```bash
# Upgrade pip and install build dependencies
pip install --upgrade pip setuptools wheel

# Try again
pip install git+https://github.com/scambus/scambus-python-client.git
```

## Using in requirements.txt

Add to your project's `requirements.txt`:

```
# Install from main branch
git+https://github.com/scambus/scambus-python-client.git

# Install specific version
git+https://github.com/scambus/scambus-python-client.git@v0.1.0

# Install with extras
git+https://github.com/scambus/scambus-python-client.git#egg=scambus[dev]
```

Then install:

```bash
pip install -r requirements.txt
```

## Using in pyproject.toml / setup.py

### pyproject.toml

```toml
[project]
dependencies = [
    "scambus @ git+https://github.com/scambus/scambus-python-client.git@v0.1.0"
]
```

### setup.py

```python
setup(
    name="your-project",
    install_requires=[
        "scambus @ git+https://github.com/scambus/scambus-python-client.git@v0.1.0"
    ]
)
```

## Docker Usage

In a Dockerfile:

```dockerfile
FROM python:3.11

# Install git (required for pip install from GitHub)
RUN apt-get update && apt-get install -y git

# Install scambus from GitHub
RUN pip install git+https://github.com/scambus/scambus-python-client.git

# Your application code
COPY . /app
WORKDIR /app

CMD ["python", "your_app.py"]
```

## GitHub Authentication (Private Repositories)

If the repository is private, you'll need authentication:

### Using Personal Access Token

```bash
# Set token as environment variable
export GITHUB_TOKEN="your_github_token"

# Install with token
pip install git+https://${GITHUB_TOKEN}@github.com/scambus/scambus-python-client.git
```

### Using SSH

```bash
# Install via SSH (requires SSH key configured)
pip install git+ssh://git@github.com/scambus/scambus-python-client.git
```

## Advantages of GitHub Installation

- ✅ Get the latest features immediately
- ✅ Test pre-release versions
- ✅ Install from feature branches
- ✅ Use in CI/CD pipelines
- ✅ No waiting for PyPI approval

## When to Use GitHub Installation

- **Pre-PyPI release**: Before package is available on PyPI
- **Development**: Testing latest unreleased features
- **Bug fixes**: Getting critical fixes before next release
- **Feature testing**: Testing specific feature branches
- **Private deployment**: If you don't want to publish to PyPI

## Migrating to PyPI

Once the package is available on PyPI, you can switch:

```bash
# Uninstall GitHub version
pip uninstall scambus

# Install from PyPI
pip install scambus
```

Or simply:

```bash
# pip will handle the switch automatically
pip install scambus
```

## Support

- **Repository**: https://github.com/scambus/scambus-python-client
- **Issues**: https://github.com/scambus/scambus-python-client/issues
- **Documentation**: See README.md in the repository

---

**Note:** Once the package is published to PyPI, it's recommended to install from PyPI (`pip install scambus`) for easier dependency management and faster installation.
