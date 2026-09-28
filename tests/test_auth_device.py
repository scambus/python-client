"""Unit tests for device login token refresh."""

import json
import time
from unittest.mock import Mock

import httpx
import pytest

from scambus_cli import auth_device

API_URL = "https://scambus.example/api"
REFRESH_URL = "https://scambus.example/api/auth/refresh"


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_device, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth_device, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(auth_device, "console", Mock())
    mgr = auth_device.DeviceAuthManager(API_URL)
    mgr._save_config(
        {
            "api_url": API_URL,
            "auth": {
                "type": "device",
                "token": "old-access",
                "refresh_token": "stored-refresh",
                "expires_at": time.time() - 10,
            },
        }
    )
    return mgr


def respond(monkeypatch, status, body=None, content=None):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        request = httpx.Request("POST", url)
        if content is not None:
            return httpx.Response(status, content=content, request=request)
        return httpx.Response(status, json=body, request=request)

    monkeypatch.setattr(auth_device.httpx, "post", fake_post)
    return calls


def stored(manager):
    return json.loads(manager.config_file.read_text())


def printed(manager):
    return " ".join(str(c.args[0]) for c in auth_device.console.print.call_args_list)


def test_refresh_200_updates_access_token_and_keeps_refresh_token(manager, monkeypatch):
    calls = respond(
        monkeypatch,
        200,
        {"access_token": "new-access", "token_type": "Bearer", "expires_in": 604800},
    )

    assert manager.get_token() == "new-access"

    assert calls == [(REFRESH_URL, {"json": {"refresh_token": "stored-refresh"}, "timeout": 10})]
    auth = stored(manager)["auth"]
    assert auth["token"] == "new-access"
    assert auth["refresh_token"] == "stored-refresh"
    assert auth["expires_at"] == pytest.approx(time.time() + 604800, abs=5)
    assert stored(manager)["api_url"] == API_URL


def test_refresh_401_removes_credentials_and_asks_for_login(manager, monkeypatch):
    respond(monkeypatch, 401, {"error": "Token has been revoked"})

    assert manager.get_token() is None

    assert "auth" not in stored(manager)
    assert stored(manager)["api_url"] == API_URL
    assert "Token has been revoked" in printed(manager)
    assert "scambus auth login" in printed(manager)


@pytest.mark.parametrize(
    "status,body,reason",
    [
        (503, {"error": "Authentication service temporarily unavailable"}, "temporarily"),
        (429, None, "HTTP 429"),
    ],
)
def test_refresh_temporary_failure_keeps_credentials(manager, monkeypatch, status, body, reason):
    before = stored(manager)
    respond(monkeypatch, status, body)

    assert manager.get_token() is None

    assert stored(manager) == before
    assert reason in printed(manager)
    assert "Your login is kept" in printed(manager)


def test_refresh_network_error_keeps_credentials(manager, monkeypatch):
    before = stored(manager)

    def fail(url, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(auth_device.httpx, "post", fail)

    assert manager.get_token() is None
    assert stored(manager) == before
    assert "Your login is kept" in printed(manager)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"body": {"token": "wrong-field"}},
        {"body": {"access_token": "new-access"}},
        {"body": {"access_token": "new-access", "expires_in": "604800"}},
        {"body": ["not", "an", "object"]},
        {"content": b"<html>gateway</html>"},
    ],
)
def test_refresh_malformed_200_keeps_credentials(manager, monkeypatch, kwargs):
    before = stored(manager)
    respond(monkeypatch, 200, **kwargs)

    assert manager.get_token() is None

    assert stored(manager) == before
    assert "unexpected response" in printed(manager)


def test_refresh_without_refresh_token_asks_for_login(manager, monkeypatch):
    config = stored(manager)
    config["auth"].pop("refresh_token")
    manager._save_config(config)
    calls = respond(monkeypatch, 200, {})

    assert manager.get_token() is None
    assert calls == []
    assert "scambus auth login" in printed(manager)


@pytest.mark.parametrize(
    "api_url,base",
    [
        ("https://scambus.app/api", "https://scambus.app"),
        ("https://scambus.app/api/", "https://scambus.app"),
        ("https://scambus.app", "https://scambus.app"),
        ("https://scambus.wiki/", "https://scambus.wiki"),
        ("https://scambus.net/api", "https://scambus.net"),
        ("http://localhost:8080/api", "http://localhost:8080"),
    ],
)
def test_api_url_removes_only_exact_api_suffix(manager, api_url, base):
    assert auth_device.DeviceAuthManager(api_url).api_url == base


def test_unexpired_token_does_not_refresh(manager, monkeypatch):
    config = stored(manager)
    config["auth"]["expires_at"] = time.time() + 3600
    manager._save_config(config)
    calls = respond(monkeypatch, 500, {})

    assert manager.get_token() == "old-access"
    assert calls == []
