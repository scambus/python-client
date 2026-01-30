#!/usr/bin/env python3
"""
Bank Account Detection Example

This example demonstrates creating a detection with a bank account identifier,
using typed classes for identifiers, details, and tags.
"""

import os
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
    """Create a detection with bank account identifier using typed classes."""

    print("=" * 60)
    print("Bank Account Detection Example")
    print("=" * 60)

    # Create bank account identifier using helper method
    print("\n1. Creating bank account identifier...")
    bank_identifier = client.create_bank_account_identifier(
        account="9876543210",
        routing="123456789",
        institution="Chase Bank",
        owner="John Doe",
        owner_address="123 Main St, New York, NY 10001",
        country="US",
        confidence=0.85,
    )
    print("Bank account identifier created")
    print(f"  Account: {bank_identifier['value']}")

    # Create detection with multiple identifier types using typed classes
    print("\n2. Creating detection with identifiers...")
    entry = client.create_detection(
        description="Bank transfer scam detected",
        details=DetectionDetails(
            data={
                "reportSource": "Customer Report",
                "amountLost": 5000.00,
                "currency": "USD",
            },
        ),
        identifiers=[
            bank_identifier,  # Bank account from helper
            IdentifierLookup(type="phone", value="+12125551234", confidence=0.9),
            IdentifierLookup(type="email", value="scammer@fraudulent-site.com", confidence=0.95),
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="BankTransfer"),
            TagLookup(tag_name="HighPriority"),
            TagLookup(tag_name="FinancialLoss"),
        ],
    )

    print(f"Created journal entry: {entry.id}")
    print(f"  Type: {entry.type}")
    print(f"  Description: {entry.description}")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Display identifiers
    print("\n  Linked Identifiers:")
    for identifier in entry.identifiers:
        confidence_str = f" (confidence: {identifier.confidence})" if identifier.confidence else ""
        print(f"    - {identifier.type}: {identifier.display_value}{confidence_str}")

    print("\nDetection with bank account created successfully!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        raise
