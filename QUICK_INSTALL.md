# Quick Install Guide

## Install from GitHub (Before PyPI)

```bash
pip install git+https://github.com/scambus/python-client.git
```

That's it! 🎉

## Verify Installation

```bash
# Test Python library
python -c "from scambus_client import ScambusClient; print('✅ Library works!')"

# Test CLI tool
scambus --help
```

## Next Steps

1. **Set up authentication:**
   ```bash
   export SCAMBUS_URL="https://api.scambus.net/api"
   export SCAMBUS_API_TOKEN="your-token"
   ```

2. **Try the library:**
   ```python
   from scambus_client import ScambusClient

   client = ScambusClient(
       api_url="https://api.scambus.net/api",
       api_token="your-token"
   )

   # Submit a detection
   detection = client.create_detection(
       description="Suspicious activity detected",
       identifiers=["email:scammer@example.com"]
   )
   ```

3. **Try the CLI:**
   ```bash
   scambus journal create-detection \
       --description "Phishing email" \
       --identifier email:scam@example.com
   ```

## More Options

**Install specific version:**
```bash
pip install git+https://github.com/scambus/python-client.git@v0.1.0
```

**Install with dev tools:**
```bash
pip install "git+https://github.com/scambus/python-client.git#egg=scambus[dev]"
```

**Upgrade to latest:**
```bash
pip install --upgrade git+https://github.com/scambus/python-client.git
```

## Need Help?

- 📖 Full guide: [INSTALL_FROM_GITHUB.md](INSTALL_FROM_GITHUB.md)
- 📚 Documentation: [README.md](README.md)
- 🐛 Issues: https://github.com/scambus/python-client/issues

## Requirements

- Python 3.8+
- pip
- git (install with `brew install git` on macOS)
