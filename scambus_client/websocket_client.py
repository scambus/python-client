"""
WebSocket client for real-time Scambus notifications and updates.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .config import get_api_url, get_api_token

logger = logging.getLogger(__name__)


class ScambusWebSocketClient:
    """
    WebSocket client for real-time notifications from Scambus API.

    Example:
        ```python
        import asyncio
        from scambus_client import ScambusClient
        from scambus_client.websocket_client import ScambusWebSocketClient

        # Initialize HTTP client for authentication
        client = ScambusClient(
            api_url="https://api.scambus.net/api",
            api_key_id="your-key-id",
            api_key_secret="your-secret"
        )

        # Create WebSocket client
        ws_client = ScambusWebSocketClient(
            api_url="https://api.scambus.net/api",
            api_key_id="your-key-id",
            api_key_secret="your-secret"
        )

        # Define notification handler
        async def handle_notification(notification):
            print(f"New notification: {notification['title']}")
            print(f"Message: {notification['message']}")

        # Start listening for notifications
        asyncio.run(ws_client.listen_notifications(handle_notification))
        ```
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key_id: Optional[str] = None,
        api_key_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        max_reconnect_attempts: int = 10,
        reconnect_delay: float = 1.0,
    ):
        """
        Initialize the WebSocket client.

        Args:
            api_url: Base URL of the Scambus API (auto-loaded from CLI config if not provided)
            api_key_id: API key ID (UUID) for authentication
            api_key_secret: API key secret for authentication
            api_token: API JWT token (auto-loaded from CLI config if not provided)
            max_reconnect_attempts: Maximum number of reconnection attempts (default: 10)
            reconnect_delay: Initial delay between reconnection attempts in seconds (default: 1.0)
        """
        # Load from CLI config if parameters not provided
        self.api_url = get_api_url(api_url)
        if api_token is None:
            api_token = get_api_token()
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_attempts = 0
        self._ws: Optional[WebSocketClientProtocol] = None
        self._running = False
        self._message_handlers: Dict[str, Dict[str, list]] = {}  # channel -> event -> [callbacks]

        # Build WebSocket URL (convert http(s):// to ws(s)://)
        parsed = urlparse(self.api_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        self.ws_url = f"{ws_scheme}://{parsed.netloc}{parsed.path}/ws"

        # Set authentication headers
        if api_key_id and api_key_secret:
            self.auth_header = ("X-API-Key", f"{api_key_id}:{api_key_secret}")
        elif api_token:
            self.auth_header = ("Authorization", f"Bearer {api_token}")
        else:
            raise ValueError("Either api_key_id/api_key_secret or api_token must be provided")

    async def connect(self) -> None:
        """Establish WebSocket connection with authentication."""
        try:
            # Create extra headers for authentication
            extra_headers = {
                self.auth_header[0]: self.auth_header[1],
                "User-Agent": "scambus-python-client/2.0.0",
            }

            logger.info(f"Connecting to WebSocket: {self.ws_url}")
            self._ws = await websockets.connect(
                self.ws_url,
                extra_headers=extra_headers,
                ping_interval=30,  # Send ping every 30 seconds
                ping_timeout=10,  # Wait 10 seconds for pong
                close_timeout=10,
            )

            self.reconnect_attempts = 0  # Reset on successful connection
            logger.info("WebSocket connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        self._running = False
        if self._ws and not self._ws.closed:
            logger.info("Closing WebSocket connection")
            await self._ws.close()
            self._ws = None

    async def _handle_message(self, message_data: str) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            message_data: Raw JSON message string
        """
        try:
            message = json.loads(message_data)

            # Extract message fields
            msg_type = message.get("type")
            channel = message.get("channel", "")
            event = message.get("event", "")
            data = message.get("data")

            # Log non-heartbeat messages
            if msg_type != "heartbeat":
                logger.debug(f"Received {msg_type}/{event} on channel {channel}")

            # Special handling for connection confirmation
            if msg_type == "connected":
                logger.info(f"WebSocket connection confirmed: {data.get('connectionId')}")
                return

            # Call registered handlers for this channel/event
            if channel in self._message_handlers:
                channel_handlers = self._message_handlers[channel]

                # Call event-specific handlers
                if event in channel_handlers:
                    for handler in channel_handlers[event]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(data)
                            else:
                                handler(data)
                        except Exception as e:
                            logger.error(f"Error in message handler: {e}", exc_info=True)

                # Call wildcard handlers (event = '*')
                if "*" in channel_handlers:
                    for handler in channel_handlers["*"]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception as e:
                            logger.error(f"Error in wildcard handler: {e}", exc_info=True)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)

    def on(self, channel: str, event: str, callback: Callable[[Any], None]) -> Callable[[], None]:
        """
        Register a callback for specific channel and event.

        Args:
            channel: Channel name (e.g., "notifications", "stats")
            event: Event type (e.g., "notification", "update") or "*" for all events
            callback: Callback function (can be sync or async)

        Returns:
            Unsubscribe function

        Example:
            ```python
            def handle_notification(data):
                print(f"Notification: {data['title']}")

            # Subscribe
            unsubscribe = ws_client.on("notifications", "notification", handle_notification)

            # Later, unsubscribe
            unsubscribe()
            ```
        """
        if channel not in self._message_handlers:
            self._message_handlers[channel] = {}

        if event not in self._message_handlers[channel]:
            self._message_handlers[channel][event] = []

        self._message_handlers[channel][event].append(callback)

        # Return unsubscribe function
        def unsubscribe():
            if (
                channel in self._message_handlers
                and event in self._message_handlers[channel]
                and callback in self._message_handlers[channel][event]
            ):
                self._message_handlers[channel][event].remove(callback)
                if not self._message_handlers[channel][event]:
                    del self._message_handlers[channel][event]
                if not self._message_handlers[channel]:
                    del self._message_handlers[channel]

        return unsubscribe

    async def _reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnected successfully, False otherwise
        """
        self.reconnect_attempts += 1

        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(
                f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Giving up."
            )
            return False

        # Exponential backoff with jitter
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), 60.0)
        logger.info(
            f"Reconnecting in {delay:.1f}s (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})"
        )
        await asyncio.sleep(delay)

        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {e}")
            return False

    async def run(self) -> None:
        """
        Run the WebSocket client with automatic reconnection.

        This method will keep running until explicitly stopped or max reconnection attempts reached.

        Example:
            ```python
            # Run in the background
            asyncio.create_task(ws_client.run())

            # Or run as main task
            asyncio.run(ws_client.run())
            ```
        """
        self._running = True

        while self._running:
            try:
                # Connect if not already connected
                if not self._ws or self._ws.closed:
                    await self.connect()

                # Listen for messages
                async for message in self._ws:
                    if isinstance(message, str):
                        await self._handle_message(message)
                    elif isinstance(message, bytes):
                        await self._handle_message(message.decode("utf-8"))

            except ConnectionClosed as e:
                if e.code == 1012:
                    # Service restart - reconnect immediately
                    logger.info("Server restarting - reconnecting immediately")
                    self.reconnect_attempts = 0  # Reset attempts for service restart
                    await asyncio.sleep(0.1)  # Brief delay
                    continue
                elif e.code == 1000:
                    # Normal closure
                    logger.info("WebSocket closed normally")
                    break
                else:
                    logger.warning(f"WebSocket connection closed: code={e.code} reason={e.reason}")

                # Attempt reconnection for abnormal closures
                if not await self._reconnect():
                    break

            except WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                if not await self._reconnect():
                    break

            except Exception as e:
                logger.error(f"Unexpected error in WebSocket client: {e}", exc_info=True)
                if not await self._reconnect():
                    break

        logger.info("WebSocket client stopped")

    async def listen_notifications(
        self,
        on_notification: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """
        Convenience method to listen for notifications.

        This is a simplified interface that:
        1. Registers the notification handler
        2. Starts the WebSocket client
        3. Runs until interrupted

        Args:
            on_notification: Callback for notification events (can be sync or async)
            on_error: Optional callback for errors (can be sync or async)

        Example:
            ```python
            async def handle_notification(notification):
                print(f"{notification['title']}: {notification['message']}")

            # This will run until interrupted (Ctrl+C)
            await ws_client.listen_notifications(handle_notification)
            ```
        """
        # Register notification handler
        self.on("notifications", "notification", on_notification)

        # Register error handler if provided
        if on_error:

            async def error_wrapper():
                try:
                    await self.run()
                except Exception as e:
                    if asyncio.iscoroutinefunction(on_error):
                        await on_error(e)
                    else:
                        on_error(e)

            await error_wrapper()
        else:
            await self.run()

    async def subscribe_stream(self, stream_id: str, cursor: str = "$") -> None:
        """
        Subscribe to an export stream for real-time messages.

        This sends a subscribe message to the server to start receiving stream messages.

        Args:
            stream_id: UUID of the export stream to subscribe to
            cursor: Starting position in the stream:
                   - "$" = from end (only new messages, default)
                   - "0-0" = from beginning (all messages)
                   - "<message-id>" = from specific message ID (e.g., "1234567890-0")

        Example:
            ```python
            # Subscribe from end (only new messages)
            await ws_client.subscribe_stream("abc-123-def-456")

            # Subscribe from beginning (get all messages)
            await ws_client.subscribe_stream("abc-123-def-456", cursor="0-0")

            # Resume from specific position
            await ws_client.subscribe_stream("abc-123-def-456", cursor="1700000000000-0")

            # Register handler for stream messages
            def handle_stream_message(data):
                print(f"Received stream message: {data}")

            ws_client.on(f"stream:{stream_id}", "message", handle_stream_message)
            ```
        """
        if not self._ws or self._ws.closed:
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        # Send subscribe message to server with cursor
        subscribe_msg = {
            "action": "subscribe",
            "channel": f"stream:{stream_id}",
            "cursor": cursor
        }

        await self._ws.send(json.dumps(subscribe_msg))
        logger.info(f"Sent subscribe request for stream: {stream_id} (cursor: {cursor})")

    async def unsubscribe_stream(self, stream_id: str) -> None:
        """
        Unsubscribe from an export stream.

        Args:
            stream_id: UUID of the export stream to unsubscribe from

        Example:
            ```python
            await ws_client.unsubscribe_stream("abc-123-def-456")
            ```
        """
        if not self._ws or self._ws.closed:
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        # Send unsubscribe message to server
        unsubscribe_msg = {
            "action": "unsubscribe",
            "channel": f"stream:{stream_id}"
        }

        await self._ws.send(json.dumps(unsubscribe_msg))
        logger.info(f"Sent unsubscribe request for stream: {stream_id}")

    async def listen_stream(
        self,
        stream_id: str,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        cursor: str = "$",
    ) -> None:
        """
        Convenience method to listen for export stream messages.

        This is a simplified interface that:
        1. Connects to WebSocket
        2. Subscribes to the stream
        3. Registers the message handler
        4. Runs until interrupted

        Args:
            stream_id: UUID of the export stream to listen to
            on_message: Callback for stream messages (can be sync or async)
            on_error: Optional callback for errors (can be sync or async)
            cursor: Starting position in the stream:
                   - "$" = from end (only new messages, default)
                   - "0-0" = from beginning (all messages)
                   - "<message-id>" = from specific message ID

        Example:
            ```python
            async def handle_message(message):
                print(f"Journal Entry: {message.get('id')}")
                print(f"Type: {message.get('type')}")
                for identifier in message.get('identifiers', []):
                    print(f"  - {identifier['type']}: {identifier['displayValue']}")

            # Listen from end (only new messages)
            await ws_client.listen_stream("abc-123-def-456", handle_message)

            # Listen from beginning (get all historical messages)
            await ws_client.listen_stream("abc-123-def-456", handle_message, cursor="0-0")
            ```
        """
        # Register message handler
        channel = f"stream:{stream_id}"
        self.on(channel, "message", on_message)

        # Connect to WebSocket
        await self.connect()

        # Subscribe to stream with cursor
        await self.subscribe_stream(stream_id, cursor=cursor)

        # Register error handler if provided
        if on_error:

            async def error_wrapper():
                try:
                    await self.run()
                except Exception as e:
                    if asyncio.iscoroutinefunction(on_error):
                        await on_error(e)
                    else:
                        on_error(e)

            await error_wrapper()
        else:
            await self.run()
