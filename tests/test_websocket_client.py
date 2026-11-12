import pytest

from scambus_client.websocket_client import ScambusWebSocketClient


@pytest.mark.parametrize(
    ("api_url", "expected"),
    [
        ("https://scambus.net/api", "wss://scambus.net/api/ws"),
        ("https://dev.scambus.net/api", "wss://dev.scambus.net/api/ws"),
        ("http://localhost:8080/api", "ws://localhost:8080/api/ws"),
    ],
)
def test_websocket_url_uses_the_api_host(api_url, expected):
    client = ScambusWebSocketClient(api_url=api_url, api_token="token")

    assert client.ws_url == expected
