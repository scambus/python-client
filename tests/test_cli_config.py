"""Unit tests for the CLI config file."""

import json
import os
import stat

import click
import pytest
from click.testing import CliRunner

from scambus_cli import auth_device, config
from scambus_cli.cli import cli


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_FILE", path)
    monkeypatch.setattr(auth_device, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth_device, "CONFIG_FILE", path)
    monkeypatch.delenv("SCAMBUS_URL", raising=False)
    return path


def test_save_config_writes_owner_only_file_without_leftovers(config_file):
    old_umask = os.umask(0)
    try:
        config.save_config({"api_url": "https://scambus.net"}, config_file)
    finally:
        os.umask(old_umask)

    assert json.loads(config_file.read_text()) == {"api_url": "https://scambus.net"}
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
    assert os.listdir(config_file.parent) == ["config.json"]


def test_save_config_failure_keeps_previous_file(config_file):
    config_file.write_text('{"auth": {"refresh_token": "keep"}}')

    with pytest.raises(TypeError):
        config.save_config({"bad": object()}, config_file)

    assert json.loads(config_file.read_text()) == {"auth": {"refresh_token": "keep"}}
    assert os.listdir(config_file.parent) == ["config.json"]


def test_load_config_missing_file_is_empty(config_file):
    assert config.load_config(config_file) == {}


@pytest.mark.parametrize("content", ['{"auth": {"refresh_token": "keep"', "[1, 2]"])
def test_load_config_corrupt_file_names_file(config_file, content):
    config_file.write_text(content)

    with pytest.raises(click.ClickException) as excinfo:
        config.load_config(config_file)

    assert str(config_file) in excinfo.value.message


def test_corrupt_config_stops_cli_and_keeps_file(config_file):
    content = '{"auth": {"type": "device", "refresh_token": "keep"'
    config_file.write_text(content)

    result = CliRunner().invoke(cli, ["auth", "logout"])

    assert result.exit_code == 1
    assert str(config_file) in result.output
    assert config_file.read_text() == content


def test_corrupt_config_stops_refresh_and_keeps_file(config_file):
    content = '{"auth": {"type": "device", "refresh_token": "keep"'
    config_file.write_text(content)
    manager = auth_device.DeviceAuthManager("https://scambus.net")

    with pytest.raises(click.ClickException):
        manager.get_token()

    assert config_file.read_text() == content
