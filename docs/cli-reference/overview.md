# CLI Overview

The Scambus CLI provides command-line access to Scambus functionality.

## Installation

```bash
pip install scambus-client[cli]
```

## Configuration

Set your API key:

```bash
export SCAMBUS_API_KEY="your-api-token"
export SCAMBUS_URL="https://api.scambus.net"  # Optional
```

## Usage

```bash
scambus --help
```

## Command Groups

- `journal` - Manage journal entries
- `search` - Search identifiers and cases
- `streams` - Manage export streams
- `cases` - Manage investigation cases
- `profile` - View and manage your profile
- `media` - Upload and manage media files
- `tags` - Manage tags

See individual command group pages for detailed documentation.
