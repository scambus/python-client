#!/usr/bin/env python3
"""
Simple Detection Example

This example demonstrates the basic workflow for creating a detection
with identifiers, tags, and typed classes.
"""

import os
from datetime import datetime, timezone
from scambus_client import (
    ScambusClient,
    DetectionDetails,
    IdentifierLookup,
    TagLookup,
)

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Create a simple phishing detection using typed classes."""

    print("=" * 60)
    print("Simple Phishing Detection Example")
    print("=" * 60)

    # Create a detection using typed classes (recommended)
    print("\n1. Creating detection with typed classes...")
    entry = client.create_detection(
        description="Phishing email detected targeting Example Corp employees",
        details=DetectionDetails(
            category="phishing",
            detected_at=datetime.now(timezone.utc),
            confidence=0.95,
            details={"targetOrganization": "Example Corp"},
        ),
        identifiers=[
            IdentifierLookup(
                type="email",
                value="scammer@fraudulent-site.com",
                confidence=0.95,
                label="sender",
            ),
            IdentifierLookup(
                type="phone",
                value="+12125551234",
                confidence=0.8,
                label="callback",
            ),
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Phishing"),
            TagLookup(tag_name="HighPriority"),
        ],
    )

    print(f"Created journal entry: {entry.id}")
    print(f"  Type: {entry.type}")
    print(f"  Description: {entry.description}")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Display identifiers
    print("\n  Linked Identifiers:")
    for identifier in entry.identifiers:
        print(f"    - {identifier.type}: {identifier.display_value} (confidence: {identifier.confidence})")

    print("\nDetection created successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        raise
