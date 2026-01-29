#!/usr/bin/env python3
"""
Simple Media Upload Example

This example demonstrates the simplified API for creating detections
with media using the new 'media' parameter.
"""

import os
import sys
from pathlib import Path
from scambus_client import ScambusClient, IdentifierLookup, DetectionDetails

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def example_single_media(screenshot_path: str):
    """Example with a single media file."""

    print("\n" + "=" * 60)
    print("Example 1: Single Media File")
    print("=" * 60)

    # Upload and create detection in one flow
    media = client.upload_media(screenshot_path, notes="Phishing site screenshot")

    entry = client.create_detection(
        description="Phishing website detected",
        details=DetectionDetails(category="phishing", confidence=0.95),
        identifiers=[
            IdentifierLookup(type="email", value="scammer@example.com", confidence=0.95),
            IdentifierLookup(type="phone", value="+12125551234", confidence=0.9),
        ],
        media=media,  # Simple! Just pass the media object
    )

    print(f"✓ Created detection: {entry.id}")
    print(f"  - {len(entry.identifiers)} identifiers linked")


def example_multiple_media():
    """Example with multiple media files."""

    print("\n" + "=" * 60)
    print("Example 2: Multiple Media Files")
    print("=" * 60)

    # Create some dummy files for demo
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f1:
        f1.write(b"Evidence document 1")
        file1 = f1.name

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f2:
        f2.write(b"Evidence document 2")
        file2 = f2.name

    try:
        # Upload multiple files
        media1 = client.upload_media(file1, notes="Email headers")
        media2 = client.upload_media(file2, notes="Email body")

        # Create detection with both media files
        entry = client.create_detection(
            description="Phishing email with multiple attachments",
            details=DetectionDetails(category="phishing"),
            identifiers=[
                IdentifierLookup(type="email", value="phisher@scam.com", confidence=1.0),
            ],
            media=[media1, media2],  # Pass list of media objects
        )

        print(f"✓ Created detection: {entry.id}")
        print(f"  - Attached 2 media files")
    finally:
        # Clean up temp files
        os.unlink(file1)
        os.unlink(file2)


def example_no_media():
    """Example without any media (identifiers only)."""

    print("\n" + "=" * 60)
    print("Example 3: Detection Without Media")
    print("=" * 60)

    entry = client.create_detection(
        description="Suspicious email reported",
        identifiers=[
            IdentifierLookup(type="email", value="suspicious@example.com", confidence=0.8),
        ],
    )

    print(f"✓ Created detection: {entry.id}")
    print(f"  - No media attached")


def main():
    """Main function."""

    print("=" * 60)
    print("Simple Media Upload Examples")
    print("=" * 60)

    # Check if screenshot path provided
    if len(sys.argv) >= 2:
        screenshot_path = sys.argv[1]

        # Verify file exists
        if not Path(screenshot_path).exists():
            print(f"Error: File not found: {screenshot_path}")
            sys.exit(1)

        example_single_media(screenshot_path)
    else:
        print("\nNote: No screenshot provided, skipping single media example")
        print("Usage: python simple_media_upload.py <screenshot_path>")

    # Run other examples
    example_multiple_media()
    example_no_media()

    print("\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
