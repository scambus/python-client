#!/usr/bin/env python3
"""
Simple Detection Example

This example demonstrates the basic workflow for creating a detection
with identifiers and evidence.
"""

import os
from datetime import datetime
from scambus_client import ScambusClient

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Create a simple phishing detection."""

    print("=" * 60)
    print("Simple Phishing Detection Example")
    print("=" * 60)

    # Create a detection without evidence
    print("\n1. Creating detection with identifiers...")
    entry = client.create_detection(
        description="Phishing email detected targeting Example Corp employees",
        details={
            "category": "phishing",
            "confidence": 0.95,
            "detectedAt": datetime.now().isoformat(),
            "targetOrganization": "Example Corp",
        },
        identifiers=[
            {"type": "email", "value": "scammer@fraudulent-site.com", "confidence": 0.95},
            {"type": "phone", "value": "+12125551234", "confidence": 0.8},
        ],
    )

    print(f"✓ Created journal entry: {entry.id}")
    print(f"  Type: {entry.type}")
    print(f"  Description: {entry.description}")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Display identifiers
    print("\n  Linked Identifiers:")
    for identifier in entry.identifiers:
        print(f"    - {identifier.type}: {identifier.display_value} (confidence: {identifier.confidence})")

    print("\n✓ Detection created successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise