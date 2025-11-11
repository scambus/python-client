"""
Example: Case Management with Scambus Client

This example demonstrates how to create and manage cases using the
Scambus Python client library.
"""

import os
from scambus_client import ScambusClient

# Initialize the client
API_URL = os.getenv("SCAMBUS_API_URL", "http://localhost:8080/api")
API_TOKEN = os.getenv("SCAMBUS_API_TOKEN")

client = ScambusClient(api_url=API_URL, api_token=API_TOKEN)


def create_case_example():
    """Create a new case for tracking a fraud investigation."""
    case = client.create_case(
        title="Phishing Campaign - January 2025",
        description="Large-scale phishing operation targeting financial institutions. "
                    "Multiple victims reported email scams with fake bank portals.",
        status="active"
    )

    print(f"✓ Created case: {case.id}")
    print(f"  Title: {case.title}")
    print(f"  Status: {case.status}")
    print(f"  Created: {case.created_at}")

    return case.id


def list_cases_example():
    """List all active cases."""
    # Get active cases only
    cases = client.list_cases(status="active", limit=10)

    print(f"\n✓ Found {len(cases)} active cases:")
    for case in cases:
        print(f"  - {case.title} ({case.status})")


def update_case_example(case_id: str):
    """Update a case with new information."""
    updated_case = client.update_case(
        case_id=case_id,
        description="Large-scale phishing operation targeting financial institutions. "
                    "Investigation ongoing. 15 victims identified so far."
    )

    print(f"\n✓ Updated case: {updated_case.id}")
    print(f"  New description: {updated_case.description}")


def get_case_details(case_id: str):
    """Get detailed information about a specific case."""
    case = client.get_case(case_id)

    print(f"\n✓ Case Details:")
    print(f"  ID: {case.id}")
    print(f"  Title: {case.title}")
    print(f"  Description: {case.description}")
    print(f"  Status: {case.status}")
    print(f"  Created: {case.created_at}")
    print(f"  Updated: {case.updated_at}")


def close_case_example(case_id: str):
    """Close a case when investigation is complete."""
    updated_case = client.update_case(
        case_id=case_id,
        status="closed"
    )

    print(f"\n✓ Closed case: {updated_case.id}")
    print(f"  Status: {updated_case.status}")


def main():
    """Run the case management examples."""
    print("=== Case Management Examples ===\n")

    # Create a new case
    case_id = create_case_example()

    # List all active cases
    list_cases_example()

    # Update the case with more details
    update_case_example(case_id)

    # Get detailed case information
    get_case_details(case_id)

    # Close the case (comment out if you want to keep it open)
    # close_case_example(case_id)

    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    main()
