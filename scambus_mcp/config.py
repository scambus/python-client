"""Configuration for the Scambus MCP server."""

import os


def get_api_url() -> str:
    return os.environ.get("SCAMBUS_API_URL", "https://scambus.net")


def get_api_key() -> tuple[str, str]:
    """Return (api_key_id, api_key_secret) from environment.

    Accepts either:
      - SCAMBUS_API_KEY=id:secret (single variable)
      - SCAMBUS_API_KEY_ID + SCAMBUS_API_KEY_SECRET (two variables)
    """
    combined = os.environ.get("SCAMBUS_API_KEY", "")
    if ":" in combined:
        key_id, secret = combined.split(":", 1)
        return key_id.strip(), secret.strip()

    key_id = os.environ.get("SCAMBUS_API_KEY_ID", "")
    secret = os.environ.get("SCAMBUS_API_KEY_SECRET", "")
    if key_id and secret:
        return key_id, secret

    raise ValueError(
        "No API key configured. Set one of:\n"
        "  SCAMBUS_API_KEY=id:secret\n"
        "  SCAMBUS_API_KEY_ID + SCAMBUS_API_KEY_SECRET"
    )
