# Authentication

The Scambus Python Client uses API key authentication to secure access to the API.

## Getting an API Key

To get an API key:

1. Log in to your Scambus account at [scambus.net](https://scambus.net)
2. Navigate to Settings → API Keys
3. Click "Generate New API Key"
4. Copy and securely store your API key

!!! warning "Keep your API key secure"
    - Never commit API keys to version control
    - Never share API keys publicly
    - Use environment variables or secure secret management
    - Rotate keys regularly

## Using API Keys

### Environment Variables (Recommended)

The most secure way to use API keys is through environment variables:

```bash
export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"
```

Then in your code:

```python
import os
from scambus_client import ScambusClient

client = ScambusClient(
    base_url=os.getenv('SCAMBUS_URL'),
    api_key=os.getenv('SCAMBUS_API_KEY')
)
```

### Direct Initialization

For testing or scripts:

```python
from scambus_client import ScambusClient

client = ScambusClient(
    base_url="https://api.scambus.net",
    api_key="your-api-key"
)
```

!!! danger "Security Risk"
    Avoid hardcoding API keys in your source code. Use environment variables or secure secret management instead.

### Configuration File

For applications, consider using a configuration file:

```python
# config.py
import os
from pathlib import Path

def load_config():
    config_file = Path.home() / '.scambus' / 'config.json'
    # Load and return configuration
    pass
```

Keep the configuration file outside of version control:

```gitignore
# .gitignore
.scambus/
config.json
```

## CLI Authentication

The CLI uses environment variables:

```bash
# Set environment variables
export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"

# Use the CLI
scambus journal create-detection --description "Test"
```

Alternatively, create a shell script:

```bash
#!/bin/bash
# scambus-env.sh

export SCAMBUS_URL="https://api.scambus.net"
export SCAMBUS_API_KEY="your-api-key"
```

Source it before using the CLI:

```bash
source scambus-env.sh
scambus journal create-detection --description "Test"
```

## Multiple Environments

For different environments (dev, staging, production):

```python
import os

ENV = os.getenv('ENV', 'production')

CONFIGS = {
    'development': {
        'base_url': 'https://dev-api.scambus.net',
        'api_key': os.getenv('SCAMBUS_DEV_API_KEY')
    },
    'staging': {
        'base_url': 'https://staging-api.scambus.net',
        'api_key': os.getenv('SCAMBUS_STAGING_API_KEY')
    },
    'production': {
        'base_url': 'https://api.scambus.net',
        'api_key': os.getenv('SCAMBUS_API_KEY')
    }
}

config = CONFIGS[ENV]
client = ScambusClient(**config)
```

## Secret Management

For production applications, use secret management services:

### AWS Secrets Manager

```python
import boto3
from scambus_client import ScambusClient

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

secret = get_secret('scambus/api-key')
client = ScambusClient(
    base_url=secret['url'],
    api_key=secret['api_key']
)
```

### HashiCorp Vault

```python
import hvac
from scambus_client import ScambusClient

vault_client = hvac.Client(url='https://vault.example.com')
vault_client.auth.approle.login(role_id='...', secret_id='...')

secret = vault_client.secrets.kv.v2.read_secret_version(
    path='scambus/api-key'
)

client = ScambusClient(
    base_url=secret['data']['data']['url'],
    api_key=secret['data']['data']['api_key']
)
```

### Environment Variable Files

For local development, use `.env` files with `python-dotenv`:

```bash
# .env (DO NOT commit to git)
SCAMBUS_URL=https://api.scambus.net
SCAMBUS_API_KEY=your-api-key
```

```python
from dotenv import load_dotenv
import os
from scambus_client import ScambusClient

load_dotenv()

client = ScambusClient(
    base_url=os.getenv('SCAMBUS_URL'),
    api_key=os.getenv('SCAMBUS_API_KEY')
)
```

## API Key Rotation

To rotate API keys:

1. Generate a new API key in the Scambus dashboard
2. Update your configuration/secrets with the new key
3. Deploy the change
4. Delete the old API key once confirmed working

## Permissions

API keys inherit the permissions of the user who created them. Ensure your user account has the necessary permissions for the operations you need to perform.

## Troubleshooting

### Authentication Error

```python
ScambusAuthenticationError: Invalid API key
```

**Solutions:**
- Verify your API key is correct
- Check that the key hasn't expired or been revoked
- Ensure you're using the correct API endpoint

### Missing API Key

```python
ValueError: API key is required
```

**Solutions:**
- Ensure `SCAMBUS_API_KEY` environment variable is set
- Check for typos in environment variable names
- Verify the environment variable is accessible in your context

## Best Practices

1. **Use Environment Variables**: Never hardcode API keys
2. **Rotate Regularly**: Change API keys every 90 days
3. **Least Privilege**: Use API keys with minimal required permissions
4. **Separate Keys**: Use different keys for different environments
5. **Monitor Usage**: Track API key usage for suspicious activity
6. **Secure Storage**: Use secret management for production
7. **Revoke Unused**: Delete API keys that are no longer needed

## Next Steps

- [Quick Start Guide](quickstart.md) - Start using the client
- [User Guide](../user-guide/journal-entries.md) - Learn about features
