#!/usr/bin/env python3
"""
Email Journal Entry Example

This example demonstrates creating email journal entries with
properly typed details and optional media attachments.
"""

import os
from datetime import datetime
from scambus_client import ScambusClient, IdentifierLookup, TagLookup

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Create email journal entries."""

    print("=" * 60)
    print("Email Journal Entry Examples")
    print("=" * 60)

    # Example 1: Inbound phishing email
    print("\n1. Creating inbound phishing email entry...")
    entry = client.create_email(
        description="Phishing email impersonating PayPal requesting account verification",
        direction="inbound",
        subject="Urgent: Verify your PayPal account",
        sent_at=datetime(2024, 1, 15, 9, 15),
        body="Dear customer,\n\nYour account requires immediate verification...",
        message_id="<12345@suspicious-domain.com>",
        headers={
            "from": "security@paypa1.com",
            "reply-to": "noreply@suspicious-domain.com",
            "dkim": "fail",
            "spf": "fail"
        },
        identifiers=[
            IdentifierLookup(type="email", value="security@paypa1.com", confidence=1.0),
            IdentifierLookup(type="email", value="noreply@suspicious-domain.com", confidence=0.95),
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="Phishing"),
        ],
    )

    print(f"✓ Created email entry: {entry.id}")
    print(f"  Direction: inbound")
    print(f"  Subject: {entry.details.get('subject')}")
    print(f"  Identifiers: {len(entry.identifiers)}")

    # Example 2: Outbound reply (investigation)
    print("\n2. Creating outbound reply entry...")
    entry = client.create_email(
        description="Reply to phishing email for investigation purposes",
        direction="outbound",
        subject="Re: Verify your PayPal account",
        sent_at=datetime.now(),
        body="I received your email and would like to verify my account details...",
        identifiers=[
            IdentifierLookup(type="email", value="security@paypa1.com", confidence=1.0),
        ],
    )

    print(f"✓ Created email entry: {entry.id}")
    print(f"  Direction: outbound")
    print(f"  Subject: {entry.details.get('subject')}")

    # Example 3: Email with HTML body and attachments
    print("\n3. Creating email with HTML body and attachments...")
    entry = client.create_email(
        description="Business email compromise attempt",
        direction="inbound",
        subject="Urgent: Wire Transfer Request",
        sent_at=datetime(2024, 1, 16, 11, 30),
        body="Please process this wire transfer immediately.",
        html_body="<html><body><p>Please process this <b>urgent</b> wire transfer...</p></body></html>",
        message_id="<wire-transfer-scam@fake-ceo.com>",
        attachments=["wire_transfer_form.pdf", "banking_details.xlsx"],
        identifiers=[
            IdentifierLookup(type="email", value="ceo@fake-company.com", confidence=0.95),
        ],
        tags=[
            TagLookup(tag_name="ScamType", tag_value="BEC"),
            TagLookup(tag_name="HighPriority"),
        ],
    )

    print(f"✓ Created email entry: {entry.id}")
    print(f"  Direction: inbound")
    print(f"  Subject: {entry.details.get('subject')}")
    print(f"  Attachments: {len(entry.details.get('attachments', []))}")

    print("\n✓ All email entries created successfully!")

    # Example 4: Email with screenshot evidence
    print("\n4. Creating email entry with screenshot...")
    print("Note: This requires an actual image file. Skipping upload for this example.")
    print("To use media, first upload with client.upload_media() then pass to create_email():")
    print("""
    # Upload screenshot
    screenshot = client.upload_media("phishing-email.png")

    # Create email entry with media
    entry = client.create_email(
        description="Phishing email with screenshot",
        direction="inbound",
        subject="Account Verification Required",
        sent_at=datetime.now(),
        media=screenshot,  # Automatically creates evidence
        identifiers=[
            IdentifierLookup(type="email", value="scammer@example.com", confidence=0.95),
        ],
    )
    """)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
