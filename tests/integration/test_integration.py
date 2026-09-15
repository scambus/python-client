"""Integration tests for ScambusClient.

These tests require a running Scambus API instance and valid credentials.
Run with: pytest -m integration

Set environment variables:
- SCAMBUS_TEST_URL: API base URL
- SCAMBUS_TEST_API_KEY: Valid API key for testing
"""

import os
from datetime import datetime, timezone

import pytest

from scambus_client import ScambusClient

# Skip all integration tests if environment variables are not set
pytestmark = pytest.mark.skipif(
    not os.getenv("SCAMBUS_TEST_URL") or not os.getenv("SCAMBUS_TEST_API_KEY"),
    reason="Integration tests require SCAMBUS_TEST_URL and SCAMBUS_TEST_API_KEY",
)


@pytest.fixture(scope="module")
def integration_client():
    """Create a client for integration testing."""
    return ScambusClient(
        base_url=os.getenv("SCAMBUS_TEST_URL"),
        api_key=os.getenv("SCAMBUS_TEST_API_KEY"),
    )


@pytest.mark.integration
class TestIntegrationJournalEntries:
    """Integration tests for journal entries."""

    def test_create_and_retrieve_detection(self, integration_client):
        """Test creating and retrieving a detection."""
        # Create detection
        entry = integration_client.create_detection(
            description="Integration test detection",
            identifiers=["email:test@example.com"],
            category="test",
            confidence=0.5,
        )

        assert entry.id is not None
        assert entry.type == "detection"

        # Retrieve it
        retrieved = integration_client.get_journal_entry(entry.id)
        assert retrieved.id == entry.id
        assert retrieved.description == "Integration test detection"

    def test_create_in_progress_phone_call(self, integration_client):
        """Test creating an in-progress phone call."""
        entry = integration_client.create_phone_call(
            description="Integration test call",
            direction="inbound",
            start_time=datetime.now(timezone.utc),
            identifiers=["phone:+1234567890"],
            in_progress=True,
        )

        assert entry.id is not None
        assert entry.start_time is not None  # CRITICAL: Verify start_time is stored
        assert entry.end_time is None  # In-progress activities should not have end_time
        assert entry.in_progress is True

        # Complete it
        completed = entry.complete(description="Call completed in integration test")
        assert completed.in_progress is False
        assert completed.end_time is not None


@pytest.mark.integration
class TestIntegrationSearch:
    """Integration tests for search functionality."""

    def test_search_identifiers(self, integration_client):
        """Test searching for identifiers."""
        results = integration_client.search_identifiers(
            query="test", identifier_type="email", limit=5
        )

        assert isinstance(results, list)
        # Results may be empty, which is fine for integration tests

    def test_search_cases(self, integration_client):
        """Test searching for cases."""
        results = integration_client.search_cases(query="test", limit=5)

        assert isinstance(results, list)
        # Results may be empty, which is fine for integration tests


@pytest.mark.integration
class TestIntegrationStreams:
    """Integration tests for export streams."""

    def test_create_and_consume_stream(self, integration_client):
        """Test creating and consuming from a stream."""
        # Create stream
        stream = integration_client.create_stream(
            name="Integration Test Stream", filters={"type": "detection"}
        )

        assert stream.id is not None
        assert stream.name == "Integration Test Stream"

        # List streams
        streams = integration_client.list_streams()
        assert any(s.id == stream.id for s in streams)

        # Consume from stream
        events = integration_client.consume_stream(stream.id, limit=5)
        assert isinstance(events, list)

        # Clean up - delete stream
        integration_client.delete_stream(stream.id)


@pytest.mark.integration
class TestIntegrationCases:
    """Integration tests for case management."""

    def test_create_and_manage_case(self, integration_client):
        """Test creating and managing a case."""
        # Create case
        case = integration_client.create_case(
            title="Integration Test Case",
            description="Case created during integration testing",
            status="open",
        )

        assert case.id is not None
        assert case.title == "Integration Test Case"

        # Update case
        updated = integration_client.update_case(case.id, status="in_progress")
        assert updated.status == "in_progress"

        # Add comment
        comment = integration_client.create_case_comment(
            case.id, comment="Integration test comment"
        )
        assert comment is not None

        # Get case
        retrieved = integration_client.get_case(case.id)
        assert retrieved.id == case.id
