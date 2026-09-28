"""
Shared configuration loading utilities for Scambus clients.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigError(ValueError):
    """The CLI config file exists but cannot be read as a JSON object."""


def load_cli_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from CLI config file.

    Args:
        path: Config file to read. Defaults to ~/.scambus/config.json.

    Returns:
        Dictionary containing config values (empty dict if the file does not exist)

    Raises:
        ConfigError: If the file cannot be read or does not contain a JSON object.
    """
    config_path = Path(path) if path else Path.home() / ".scambus" / "config.json"
    fix = "Fix or remove the file, then try again."

    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        raise ConfigError(f"Cannot read config file {config_path}: {e}. {fix}")
    if not isinstance(config, dict):
        raise ConfigError(f"Config file {config_path} does not contain a JSON object. {fix}")
    return config


def get_api_url(api_url: Optional[str] = None) -> str:
    """
    Get API URL from provided value, environment variable, or config file.

    Priority: explicit parameter > env var > config file > default

    Args:
        api_url: Explicitly provided API URL (highest priority)

    Returns:
        API URL string
    """
    if api_url is not None:
        return api_url.rstrip("/")

    # Check environment variables (SCAMBUS_API_URL preferred, SCAMBUS_URL for backwards compat)
    env_url = os.getenv("SCAMBUS_API_URL") or os.getenv("SCAMBUS_URL")
    if env_url:
        return env_url.rstrip("/")

    # Check config file
    config = load_cli_config()
    config_url = config.get("api_url")
    if config_url:
        return config_url.rstrip("/")

    # Default
    return "https://scambus.net/api"


def get_api_token(api_token: Optional[str] = None) -> Optional[str]:
    """
    Get API token from provided value, environment variable, or config file.

    Priority: explicit parameter > env var > config file

    Args:
        api_token: Explicitly provided API token (highest priority)

    Returns:
        API token string or None if not found
    """
    if api_token is not None:
        return api_token

    # Check environment variable
    env_token = os.getenv("SCAMBUS_API_TOKEN")
    if env_token:
        return env_token

    # Check config file (CLI stores token under different keys depending on auth type)
    config = load_cli_config()
    # Try nested "auth.token" (device flow, freshest), then "jwt_token", then legacy "token"
    auth = config.get("auth")
    if isinstance(auth, dict):
        token = auth.get("token")
        if token:
            return token
    return config.get("jwt_token") or config.get("token")


def get_api_key_id(api_key_id: Optional[str] = None) -> Optional[str]:
    """
    Get API key ID from provided value or environment variable.

    Priority: explicit parameter > env var

    Args:
        api_key_id: Explicitly provided API key ID (highest priority)

    Returns:
        API key ID string or None if not found
    """
    if api_key_id is not None:
        return api_key_id

    return os.getenv("SCAMBUS_API_KEY_ID")


def get_api_key_secret(api_key_secret: Optional[str] = None) -> Optional[str]:
    """
    Get API key secret from provided value or environment variable.

    Priority: explicit parameter > env var

    Args:
        api_key_secret: Explicitly provided API key secret (highest priority)

    Returns:
        API key secret string or None if not found
    """
    if api_key_secret is not None:
        return api_key_secret

    return os.getenv("SCAMBUS_API_KEY_SECRET")
