#!/usr/bin/env python3
"""
Reports Example

This example demonstrates how to generate and download reports:
- Generate reports for identifiers
- Generate reports for journal entries
- Generate reports from views
- Check report status and download
"""

import os
import time
from scambus_client import ScambusClient

# Configuration
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN", "your-token-here")

# Initialize client
client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def main():
    """Demonstrate report generation operations."""

    print("=" * 60)
    print("Reports Example")
    print("=" * 60)

    # =========================================================================
    # Generate Identifier Report
    # =========================================================================
    print("\n1. Generating identifier report...")

    # First, find an identifier to report on
    identifiers = client.search_identifiers(identifier_type="phone", limit=1)

    if identifiers:
        identifier = identifiers[0]
        print(f"   Generating report for: {identifier.display_value}")

        report = client.generate_identifier_report(
            identifier_id=identifier.id,
            format="pdf",  # or "csv"
            include_journal_entries=True,
            include_tags=True,
        )

        report_id = report.get("id")
        print(f"   ✓ Report queued: {report_id}")

        # Wait for report
        print("   Waiting for report generation...")
        completed_report = client.wait_for_report(report_id, timeout=60)
        print(f"   ✓ Report ready: {completed_report.get('status')}")

        # Download report
        output_path = f"identifier_report_{identifier.id[:8]}.pdf"
        client.download_report(report_id, output_path)
        print(f"   ✓ Downloaded: {output_path}")
    else:
        print("   No identifiers found, skipping identifier report")

    # =========================================================================
    # Generate Journal Entry Report
    # =========================================================================
    print("\n2. Generating journal entry report...")

    # Get a recent journal entry
    my_journal = client.execute_my_journal_entries(limit=1)
    entries = my_journal.get("data", [])

    if entries:
        entry = entries[0]
        entry_id = entry.get("id")
        print(f"   Generating report for entry: {entry_id[:8]}...")

        report = client.generate_journal_entry_report(
            journal_entry_id=entry_id,
            format="pdf",
            include_identifiers=True,
            include_evidence=True,
        )

        report_id = report.get("id")
        print(f"   ✓ Report queued: {report_id}")

        # Wait and download
        completed_report = client.wait_for_report(report_id, timeout=60)
        output_path = f"journal_entry_report_{entry_id[:8]}.pdf"
        client.download_report(report_id, output_path)
        print(f"   ✓ Downloaded: {output_path}")
    else:
        print("   No journal entries found, skipping entry report")

    # =========================================================================
    # Generate View Report
    # =========================================================================
    print("\n3. Generating report from a view...")

    # Get available views
    views = client.list_views()

    if views:
        view = views[0]
        print(f"   Generating report for view: {view.name}")

        report = client.generate_view_report(
            view_id=view.id,
            format="csv",  # CSV is good for bulk data
            limit=100,  # Limit rows in report
        )

        report_id = report.get("id")
        print(f"   ✓ Report queued: {report_id}")

        # Wait and download
        completed_report = client.wait_for_report(report_id, timeout=120)
        output_path = f"view_report_{view.id[:8]}.csv"
        client.download_report(report_id, output_path)
        print(f"   ✓ Downloaded: {output_path}")
    else:
        print("   No views found, skipping view report")

    # =========================================================================
    # Manual Status Checking
    # =========================================================================
    print("\n4. Manual status checking example...")

    print("   (Demonstrating manual polling instead of wait_for_report)")

    # Create a report
    if identifiers:
        report = client.generate_identifier_report(
            identifier_id=identifiers[0].id,
            format="pdf"
        )
        report_id = report.get("id")

        # Poll for status manually
        max_attempts = 10
        for attempt in range(max_attempts):
            status = client.get_report_status(report_id)
            current_status = status.get("status")
            print(f"   Attempt {attempt + 1}: {current_status}")

            if current_status == "completed":
                print("   ✓ Report is ready!")
                break
            elif current_status == "failed":
                print(f"   ✗ Report failed: {status.get('error')}")
                break
            else:
                time.sleep(2)
        else:
            print("   ✗ Timed out waiting for report")

    print("\n✓ Reports example completed!")


def report_formats():
    """
    Information about available report formats.
    """
    print("\n" + "=" * 60)
    print("Report Formats")
    print("=" * 60)

    print("""
    Available formats:

    PDF:
    - Best for human-readable reports
    - Includes formatting and layout
    - Good for sharing and archiving

    CSV:
    - Best for data analysis
    - Can be opened in Excel, Google Sheets
    - Good for bulk exports
    - Easier to process programmatically

    Report types:

    Identifier Report:
    - History of an identifier
    - Related journal entries
    - Applied tags
    - Confidence changes over time

    Journal Entry Report:
    - Full entry details
    - Linked identifiers
    - Evidence/attachments
    - Comments and updates

    View Report:
    - Results from a saved query
    - Bulk export of matching entries
    - Useful for periodic reporting
    """)


if __name__ == "__main__":
    try:
        main()
        # Uncomment to see format information:
        # report_formats()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
