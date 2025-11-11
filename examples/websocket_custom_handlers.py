"""
Example: Custom WebSocket event handlers

This example demonstrates how to use custom event handlers for
different channels and events, including notifications and stats updates.
"""

import asyncio
import os

from scambus_client import ScambusWebSocketClient

# Get API credentials from environment variables
API_URL = os.getenv("SCAMBUS_API_URL", "https://api.scambus.net/api")
API_KEY_ID = os.getenv("SCAMBUS_API_KEY_ID")
API_KEY_SECRET = os.getenv("SCAMBUS_API_KEY_SECRET")

if not API_KEY_ID or not API_KEY_SECRET:
    print("Error: Please set SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET environment variables")
    exit(1)


async def main():
    """Set up custom WebSocket event handlers."""
    # Create WebSocket client
    ws_client = ScambusWebSocketClient(
        api_url=API_URL,
        api_key_id=API_KEY_ID,
        api_key_secret=API_KEY_SECRET,
        max_reconnect_attempts=10,
        reconnect_delay=1.0,
    )

    # Handler for notification events
    async def handle_notification(data):
        print(f"\n📬 Notification: {data.get('title')}")
        print(f"   Message: {data.get('message')}")
        print(f"   Severity: {data.get('severity', 'info')}")

    # Handler for stats updates
    async def handle_stats(data):
        print(f"\n📊 Stats Update:")
        print(f"   {data}")

    # Wildcard handler for notifications channel (receives all events)
    async def handle_all_notification_events(message):
        msg_type = message.get("type")
        event = message.get("event")
        print(f"\n🔔 Notification channel event: {msg_type}/{event}")

    # Register event handlers
    print("Setting up event handlers...")
    unsubscribe_notification = ws_client.on("notifications", "notification", handle_notification)
    unsubscribe_stats = ws_client.on("stats", "update", handle_stats)
    unsubscribe_wildcard = ws_client.on("notifications", "*", handle_all_notification_events)

    print(f"🔌 Connecting to WebSocket at {API_URL}/ws")
    print("Listening for real-time events... (Press Ctrl+C to stop)")
    print("-" * 80)

    try:
        # Start the WebSocket client
        await ws_client.run()
    except KeyboardInterrupt:
        print("\n\n👋 Disconnecting...")
        # Unsubscribe from events
        unsubscribe_notification()
        unsubscribe_stats()
        unsubscribe_wildcard()
        # Disconnect
        await ws_client.disconnect()
        print("✅ Disconnected successfully")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
