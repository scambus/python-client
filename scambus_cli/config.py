"""Configuration management for Scambus CLI."""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import click

from scambus_client.config import ConfigError, load_cli_config

# Config directory
CONFIG_DIR = Path.home() / ".scambus"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config(path: Path) -> dict:
    """Load the config file, or return an empty config if the file does not exist.

    Raises:
        click.ClickException: If the file cannot be read or is not a JSON object.
    """
    try:
        return load_cli_config(path)
    except ConfigError as e:
        raise click.ClickException(str(e))


def save_config(config: dict, path: Path) -> None:
    """Replace the config file atomically with a file that only the owner can read."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def get_api_url() -> str:
    """Get API URL from environment or config file or use default."""
    # First check environment variable
    env_url = os.getenv("SCAMBUS_URL")
    if env_url:
        return env_url

    # Then check config file
    config = load_config(CONFIG_FILE)
    config_url = config.get("api_url")
    if config_url:
        return config_url

    # Default
    return "https://scambus.net"


def set_api_url(url: str):
    """Save API URL to config file."""
    config = load_config(CONFIG_FILE)
    config["api_url"] = url
    save_config(config, CONFIG_FILE)


def get_api_token() -> Optional[str]:
    """Get API token from environment."""
    return os.getenv("SCAMBUS_API_KEY")
