"""
Example: Using the async Scambus client.

The AsyncScambusClient mirrors the sync ScambusClient API but with
async/await support, making it ideal for FastAPI, aiohttp, and other
async frameworks.
"""

import asyncio

from scambus_client import AsyncScambusClient


async def main():
    # Use as an async context manager (recommended)
    async with AsyncScambusClient(
        api_url="https://scambus.net/api",
        # Uses CLI auth automatically, or set:
        # api_key_id="your-key-id",
        # api_key_secret="your-secret",
    ) as client:
        # List recent journal entries
        entries = await client.list_journal_entries(limit=10)
        for entry in entries:
            print(f"  [{entry.type}] {entry.description}")

        # Search identifiers
        result = await client.search_identifiers(
            query="example.com",
            types=["email"],
            limit=5,
        )
        for identifier in result["data"]:
            print(f"  {identifier.type}: {identifier.value}")

        # Create a detection
        entry = await client.create_detection(
            description="Async detection example",
            identifiers=[
                {"type": "email", "value": "test@example.com", "confidence": 0.9}
            ],
        )
        print(f"Created entry: {entry.id}")


if __name__ == "__main__":
    asyncio.run(main())
