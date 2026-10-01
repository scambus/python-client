"""Unit tests for device login token refresh."""

import base64
import json
import time
from unittest.mock import Mock

import httpx
import pytest
from click.testing import CliRunner

from scambus_cli import auth_device, cli
from scambus_cli.commands.search import search
from scambus_client import websocket_client

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


def test_api_key_login_posts_access_key_id_and_secret(manager, monkeypatch):
    calls = respond(monkeypatch, 200, {"token": "api-key-jwt"})

    assert manager.api_key_login("key-id:se:cret") == "api-key-jwt"

    assert calls == [
        (
            "https://scambus.example/api/auth/apikey",
            {"json": {"accessKeyId": "key-id", "secretAccessKey": "se:cret"}, "timeout": 10},
        )
    ]
    assert stored(manager)["auth"]["token"] == "api-key-jwt"


def jwt_with_exp(exp):
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).rstrip(b"=")
    return f"header.{payload.decode()}.signature"


def test_api_key_login_stores_token_expiry(manager, monkeypatch):
    exp = int(time.time()) + 86400
    respond(monkeypatch, 200, {"token": jwt_with_exp(exp)})

    manager.api_key_login("key-id:secret")

    assert stored(manager)["auth"]["expires_at"] == exp


def test_expired_api_key_token_is_exchanged_again(manager, monkeypatch):
    renewed = jwt_with_exp(int(time.time()) + 86400)
    manager._save_config(
        {
            "api_url": API_URL,
            "auth": {
                "type": "apikey",
                "token": "expired-jwt",
                "api_key": "key-id:secret",
                "expires_at": time.time() - 10,
            },
        }
    )
    calls = respond(monkeypatch, 200, {"token": renewed})

    assert manager.get_token() == renewed

    assert len(calls) == 1
    assert calls[0][1]["json"] == {"accessKeyId": "key-id", "secretAccessKey": "secret"}
    assert stored(manager)["auth"]["token"] == renewed
    assert stored(manager)["auth"]["api_key"] == "key-id:secret"


def save_expired_api_key_login(manager):
    manager._save_config(
        {
            "api_url": API_URL,
            "auth": {
                "type": "apikey",
                "token": "expired-jwt",
                "api_key": "key-id:secret",
                "expires_at": time.time() - 10,
            },
        }
    )


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"status": 200, "body": {"not_token": "x"}}, "unexpected response"),
        ({"status": 200, "content": b"<html>gateway</html>"}, "unexpected response"),
        ({"status": 503, "body": {"error": "Service unavailable"}}, "temporarily unavailable"),
        ({"status": 401, "content": b"Invalid credentials"}, "HTTP 401"),
    ],
)
def test_failed_api_key_renewal_keeps_login_and_prints_one_message(
    manager, monkeypatch, kwargs, expected
):
    save_expired_api_key_login(manager)
    before = stored(manager)
    respond(monkeypatch, **kwargs)

    cli_messages = ensure_authenticated(monkeypatch)

    assert stored(manager) == before
    assert cli_messages == []
    assert len(refresh_messages()) == 1
    assert expected in refresh_messages()[0]


def test_api_key_token_with_unreadable_expiry_is_not_exchanged(manager, monkeypatch):
    respond(monkeypatch, 200, {"token": "not-a-jwt"})
    manager.api_key_login("key-id:secret")
    calls = respond(monkeypatch, 500, {})

    assert manager.get_token() == "not-a-jwt"
    assert calls == []


def test_unexpired_api_key_token_is_not_exchanged(manager, monkeypatch):
    manager._save_config(
        {
            "api_url": API_URL,
            "auth": {
                "type": "apikey",
                "token": "current-jwt",
                "api_key": "key-id:secret",
                "expires_at": time.time() + 3600,
            },
        }
    )
    calls = respond(monkeypatch, 500, {})

    assert manager.get_token() == "current-jwt"
    assert calls == []


@pytest.mark.parametrize("api_key", ["no-separator", ":secret", "key-id:"])
def test_api_key_login_refuses_key_without_id_and_secret(manager, monkeypatch, api_key):
    calls = respond(monkeypatch, 200, {"token": "api-key-jwt"})

    assert manager.api_key_login(api_key) is None
    assert calls == []


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


def ensure_authenticated(monkeypatch):
    monkeypatch.setenv("SCAMBUS_URL", API_URL)
    monkeypatch.setattr(cli, "console", Mock())
    with pytest.raises(SystemExit):
        cli.Context().ensure_authenticated()
    return [str(c.args[0]) for c in cli.console.print.call_args_list]


def refresh_messages():
    return [str(c.args[0]) for c in auth_device.console.print.call_args_list]


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            {"status": 503, "body": {"error": "Authentication service temporarily unavailable"}},
            "Your login is kept",
        ),
        ({"status": 429, "body": None}, "Your login is kept"),
        ({"status": 200, "body": {"token": "wrong-field"}}, "Your login is kept"),
        ({"status": 500, "body": {"error": "boom"}}, "HTTP 500: boom"),
        ({"status": 401, "body": {"error": "Invalid token"}}, "scambus auth login"),
    ],
)
def test_failed_refresh_prints_exactly_one_message(manager, monkeypatch, kwargs, expected):
    respond(monkeypatch, **kwargs)

    cli_messages = ensure_authenticated(monkeypatch)

    assert cli_messages == []
    assert len(refresh_messages()) == 1
    assert expected in refresh_messages()[0]


def test_refresh_500_keeps_credentials(manager, monkeypatch):
    before = stored(manager)
    respond(monkeypatch, 500, {"error": "boom"})

    assert manager.get_token() is None
    assert stored(manager) == before


def test_missing_credentials_prints_not_authenticated(manager, monkeypatch):
    manager._save_config({"api_url": API_URL})

    cli_messages = ensure_authenticated(monkeypatch)

    assert len(cli_messages) == 1
    assert "Not authenticated" in cli_messages[0]
    assert refresh_messages() == []


class FollowClient:
    def __init__(self):
        self.deleted = []

    def create_temporary_stream(self, **kwargs):
        return Mock(id="stream-1")

    def delete_stream(self, stream_id):
        self.deleted.append(stream_id)


@pytest.mark.parametrize("has_login", [True, False])
def test_search_follow_without_token_exits_before_websocket(manager, monkeypatch, has_login):
    if not has_login:
        manager._save_config({"api_url": API_URL})
    respond(monkeypatch, 503, {"error": "Authentication service temporarily unavailable"})
    monkeypatch.setenv("SCAMBUS_URL", API_URL)
    websocket = Mock()
    monkeypatch.setattr(websocket_client, "ScambusWebSocketClient", websocket)
    client = FollowClient()
    obj = Mock(get_client=Mock(return_value=client))

    result = CliRunner().invoke(search, ["identifiers", "--type", "phone", "--follow"], obj=obj)

    assert result.exit_code == 1
    websocket.assert_not_called()
    assert client.deleted == ["stream-1"]
    assert ("Not authenticated" in result.output) is not has_login
