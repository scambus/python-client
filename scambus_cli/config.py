"""Configuration management for Scambus CLI."""

import json
import os
from pathlib import Path
from typing import Optional

# Config directory
CONFIG_DIR = Path.home() / ".scambus"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(config: dict):
    """Save configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    CONFIG_FILE.chmod(0o600)


def get_api_url() -> str:
    """Get API URL from environment or config file or use default."""
    # First check environment variable
    env_url = os.getenv("SCAMBUS_URL")
    if env_url:
        return env_url

    # Then check config file
    config = _load_config()
    config_url = config.get("api_url")
    if config_url:
        return config_url

    # Default
    return "https://scambus.net"


def set_api_url(url: str):
    """Save API URL to config file."""
    config = _load_config()
    config["api_url"] = url
    _save_config(config)


def get_api_token() -> Optional[str]:
    """Get API token from environment."""
    return os.getenv("SCAMBUS_API_KEY")
