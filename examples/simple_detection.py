#!/usr/bin/env python3
"""
Simple Detection Example

This example demonstrates the basic workflow for creating a detection
with identifiers, tags, and typed classes. It also shows how to handle
identifiers that fail validation.
"""

import os
from scambus_client import (
    ScambusClient,
    DetectionDetails,
    IdentifierLookup,
    TagLookup,
    FailedIdentifier,
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

    # Create a simple detection — details is optional
    print("\n1. Creating detection without details...")
    entry = client.create_detection(
        description="Phishing email detected targeting Example Corp employees",
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
        print(
            f"    - {identifier.type}: {identifier.display_value} (confidence: {identifier.confidence})"
        )

    # Create a detection with freeform data attached
    print("\n2. Creating detection with freeform details data...")
    entry2 = client.create_detection(
        description="Automated scan found suspicious domain",
        details=DetectionDetails(
            data={
                "scanEngine": "PhishDetector v2.1",
                "targetOrganization": "Example Corp",
                "riskScore": 95,
            },
        ),
        identifiers=[
            IdentifierLookup(type="url", value="https://fake-bank.example.com", confidence=0.9),
        ],
    )

    print(f"Created journal entry: {entry2.id}")
    print(f"  Type: {entry2.type}")
    print(f"  Description: {entry2.description}")

    print("\nDetections created successfully!")


def example_with_failed_identifiers():
    """
    Demonstrate handling of failed identifier validation.

    When creating journal entries, identifiers that fail validation are
    skipped rather than failing the entire request. The returned entry
    includes a `failed_identifiers` field with details about what failed.
    """

    print("\n" + "=" * 60)
    print("Example: Handling Failed Identifier Validation")
    print("=" * 60)

    # Create detection with mix of valid and invalid identifiers
    print("\n1. Creating detection with mixed valid/invalid identifiers...")
    entry = client.create_detection(
        description="Detection with identifier validation examples",
        identifiers=[
            # Valid identifiers
            IdentifierLookup(type="phone", value="+12025551234", confidence=0.95),
            IdentifierLookup(type="email", value="valid@example.com", confidence=0.9),
            # Invalid identifiers (will be skipped)
            IdentifierLookup(type="phone", value="555-1234", confidence=0.8),  # Not E.164
            IdentifierLookup(type="email", value="not-an-email", confidence=0.7),  # Invalid format
        ],
    )

    print(f"\nEntry created: {entry.id}")
    print(f"Valid identifiers linked: {len(entry.identifiers)}")

    # Display linked identifiers
    print("\n  Successfully linked identifiers:")
    for identifier in entry.identifiers:
        print(f"    - {identifier.type}: {identifier.display_value}")

    # Check for failed identifiers
    if entry.failed_identifiers:
        print(f"\n  Failed identifiers ({len(entry.failed_identifiers)}):")
        for failed in entry.failed_identifiers:
            print(f"    - {failed.type}={failed.value}")
            print(f"      Reason: {failed.reason}")
    else:
        print("\n  No identifiers failed validation.")

    print("\nNote: The entry was created successfully even though some")
    print("identifiers failed validation. Always check `failed_identifiers`")
    print("if you need to know which identifiers were skipped.")


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see failed identifier handling example:
        # example_with_failed_identifiers()
    except Exception as e:
        print(f"\nError: {e}")
        raise
