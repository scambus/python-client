"""Tests that the client reads the response shapes the server sends."""

from unittest.mock import Mock

import pytest

from scambus_client import ScambusAPIError


def _respond(client, status, body):
    response = Mock()
    response.status_code = status
    response.json.return_value = body
    response.text = str(body)
    response.headers = {}
    client.session.request.return_value = response


def test_list_sessions_reads_sessions_key(client):
    session = {
        "id": "s-1",
        "jti": "jti-1",
        "user_id": "u-1",
        "user_type": "internal",
        "clerk_user_id": "user_1",
        "expires_at": "2026-12-01T00:00:00Z",
        "last_activity_at": "2026-11-11T00:00:00Z",
        "created_at": "2026-11-01T00:00:00Z",
    }
    _respond(client, 200, {"sessions": [session], "total": 1})

    assert [s.id for s in client.list_sessions()] == ["s-1"]


def test_list_sessions_raises_on_malformed_response(client):
    _respond(client, 200, [{"id": "s-1"}])

    with pytest.raises(ScambusAPIError, match="Unexpected response from GET /sessions"):
        client.list_sessions()


def test_list_passkeys_raises_on_malformed_response(client):
    _respond(client, 200, {"passkeys": []})

    with pytest.raises(ScambusAPIError, match="Unexpected response from GET /passkeys"):
        client.list_passkeys()


def test_error_message_includes_server_detail(client):
    _respond(client, 409, {"error": "leased", "detail": "The profile is leased by another user."})

    with pytest.raises(ScambusAPIError, match="leased: The profile is leased by another user."):
        client.get_browser_profile("p-1")
