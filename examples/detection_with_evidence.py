#!/usr/bin/env python3
"""
Detection with Evidence Example

This example demonstrates uploading media and creating a detection
with evidence attached.
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from scambus_client import ScambusClient, IdentifierLookup, DetectionDetails, Evidence

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_detection_with_screenshot(screenshot_path: str, url: str, identifiers: list):
    """
    Create a phishing detection with screenshot evidence.

    Args:
        screenshot_path: Path to screenshot file
        url: URL of the phishing site
        identifiers: List of identifiers found
    """

    print("=" * 60)
    print("Detection with Evidence Example")
    print("=" * 60)

    # Step 1: Upload screenshot
    print(f"\n1. Uploading screenshot: {screenshot_path}")
    media = client.upload_media(
        screenshot_path, notes=f"Screenshot of phishing site: {url}"
    )
    print(f"✓ Uploaded media: {media.id}")
    print(f"  Filename: {media.file_name}")
    print(f"  Size: {media.file_size} bytes")
    print(f"  MIME type: {media.mime_type}")

    # Step 2: Create detection with evidence
    print(f"\n2. Creating detection with evidence...")
    entry = client.create_detection(
        description=f"Phishing website detected: {url}",
        details=DetectionDetails(
            category="phishing",
            confidence=0.95,
            detected_at=datetime.now(),
            details={
                "maliciousUrl": url,
                "scanEngine": "PhishDetector v2.1",
                "riskScore": 95,
            },
        ),
        identifiers=identifiers,
        evidence=Evidence(
            type="screenshot",
            title="Phishing Website Screenshot",
            description=f"Screenshot showing fraudulent website at {url}",
            source="Automated Web Scanner - PhishDetector v2.1",
            collected_at=datetime.now(),
            media_ids=[media.id],
        ),
    )

    print(f"✓ Created journal entry: {entry.id}")
    print(f"  Type: {entry.type}")
    print(f"  Description: {entry.description}")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Display identifiers
    print("\n  Linked Identifiers:")
    for identifier in entry.identifiers:
        confidence_str = (
            f" (confidence: {identifier.confidence})" if identifier.confidence else ""
        )
        print(f"    - {identifier.type}: {identifier.display_value}{confidence_str}")

    print("\n✓ Detection with evidence created successfully!")

    return entry


def main():
    """Main function."""

    # Check if screenshot path provided
    if len(sys.argv) < 2:
        print("Usage: python detection_with_evidence.py <screenshot_path>")
        print("\nExample:")
        print("  python detection_with_evidence.py phishing-screenshot.png")
        sys.exit(1)

    screenshot_path = sys.argv[1]

    # Verify file exists
    if not Path(screenshot_path).exists():
        print(f"Error: File not found: {screenshot_path}")
        sys.exit(1)

    # Example data
    url = "http://chase-secure-login.suspicious-domain.com"
    identifiers = [
        IdentifierLookup(type="phone", value="+12125551234", confidence=0.9),
        IdentifierLookup(type="email", value="scammer@fraudulent-site.com", confidence=0.95),
    ]

    # Create detection
    entry = create_detection_with_screenshot(screenshot_path, url, identifiers)

    print(f"\n{'=' * 60}")
    print(f"Journal Entry ID: {entry.id}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise