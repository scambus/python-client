"""
Example: Real-time notifications via WebSocket

This example demonstrates how to receive real-time notifications
from the Scambus API using WebSocket connections.
"""

import asyncio
import os

from scambus_client import ScambusClient

# Get API credentials from environment variables
API_URL = os.getenv("SCAMBUS_API_URL", "https://api.scambus.net/api")
API_KEY_ID = os.getenv("SCAMBUS_API_KEY_ID")
API_KEY_SECRET = os.getenv("SCAMBUS_API_KEY_SECRET")

if not API_KEY_ID or not API_KEY_SECRET:
    print("Error: Please set SCAMBUS_API_KEY_ID and SCAMBUS_API_KEY_SECRET environment variables")
    exit(1)


async def main():
    """Listen for real-time notifications via WebSocket."""
    # Initialize HTTP client
    client = ScambusClient(api_url=API_URL, api_key_id=API_KEY_ID, api_key_secret=API_KEY_SECRET)

    # Create WebSocket client
    ws_client = client.create_websocket_client()

    # Define notification handler
    async def handle_notification(notification):
        """Handle incoming notification."""
        print("\n" + "=" * 80)
        print(f"📬 New Notification")
        print("=" * 80)
        print(f"Type: {notification.get('type', 'N/A')}")
        print(f"Title: {notification.get('title', 'N/A')}")
        print(f"Message: {notification.get('message', 'N/A')}")
        print(f"Severity: {notification.get('severity', 'N/A')}")
        print(f"Created: {notification.get('created_at', 'N/A')}")
        print(f"Read: {notification.get('read', False)}")
        print("=" * 80)
        print()

    # Define error handler
    async def handle_error(error):
        """Handle WebSocket errors."""
        print(f"\n❌ WebSocket error: {error}")

    print(f"🔌 Connecting to WebSocket at {API_URL}/ws")
    print("Listening for real-time notifications... (Press Ctrl+C to stop)")
    print("-" * 80)

    try:
        # Start listening for notifications
        # This will run until interrupted (Ctrl+C)
        await ws_client.listen_notifications(handle_notification, handle_error)
    except KeyboardInterrupt:
        print("\n\n👋 Disconnecting...")
        await ws_client.disconnect()
        print("✅ Disconnected successfully")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
