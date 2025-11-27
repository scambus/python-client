"""
Shared configuration loading utilities for Scambus clients.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


def load_cli_config() -> Dict[str, Any]:
    """
    Load configuration from CLI config file.

    Returns:
        Dictionary containing config values (empty dict if file not found or invalid)
    """
    config_path = Path.home() / ".scambus" / "config.json"

    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def get_api_url(api_url: Optional[str] = None) -> str:
    """
    Get API URL from provided value, environment variable, or config file.

    Priority: explicit parameter > SCAMBUS_URL env var > config file > default

    Args:
        api_url: Explicitly provided API URL (highest priority)

    Returns:
        API URL string
    """
    if api_url is not None:
        return api_url.rstrip("/")

    # Check environment variable
    env_url = os.getenv("SCAMBUS_URL")
    if env_url:
        return env_url.rstrip("/")

    # Check config file
    config = load_cli_config()
    config_url = config.get("api_url")
    if config_url:
        return config_url.rstrip("/")

    # Default
    return "http://localhost:8080/api"


def get_api_token(api_token: Optional[str] = None) -> Optional[str]:
    """
    Get API token from provided value or config file.

    Args:
        api_token: Explicitly provided API token (highest priority)

    Returns:
        API token string or None if not found
    """
    if api_token is not None:
        return api_token

    # Check config file
    config = load_cli_config()
    return config.get("token")
