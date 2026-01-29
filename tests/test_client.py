"""Unit tests for ScambusClient."""

from datetime import datetime, timezone

import pytest

from scambus_client import (
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusClient,
    ScambusNotFoundError,
    ScambusValidationError,
)
from scambus_client.models import Case, ExportStream, Identifier, JournalEntry


class TestScambusClientInit:
    """Test ScambusClient initialization."""

    def test_init_with_credentials(self, mock_api_url, mock_api_key):
        """Test client initialization with API token."""
        client = ScambusClient(api_url=mock_api_url, api_token=mock_api_key)
        # Client appends /api if not already present
        assert client.api_url == f"{mock_api_url}/api"
        assert client.session is not None
        assert "Authorization" in client.session.headers

    def test_init_without_api_key(self, mock_api_url):
        """Test client initialization without API key raises ValueError."""
        with pytest.raises(ValueError, match="No authentication provided"):
            ScambusClient(api_url=mock_api_url)


class TestScambusClientJournalEntries:
    """Test journal entry methods."""

    def test_create_detection(self, client, mock_journal_entry_data):
        """Test creating a detection journal entry."""
        from unittest.mock import Mock

        # First call (POST) returns just the ID
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-123"}

        # Second call (GET) returns the full entry with nested structure
        # Backend returns: {"journal_entry": {"journal_entry": {...}, "can_edit": bool}, "cases": [...]}
        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {
                "journal_entry": mock_journal_entry_data,
                "can_edit": True
            },
            "cases": []
        }

        # Configure mock to return different responses for POST and GET
        client.session.request.side_effect = [post_response, get_response]

        entry = client.create_detection(
            description="Test detection",
            identifiers=["email:scammer@example.com"],
            details={"category": "phishing", "confidence": 0.9},
        )

        assert isinstance(entry, JournalEntry)
        assert entry.id == "entry-123"
        assert entry.type == "detection"
        assert client.session.request.call_count == 2  # POST + GET

    def test_create_phone_call(self, client, mock_phone_call_data):
        """Test creating a phone call journal entry."""
        from unittest.mock import Mock

        # First call (POST) returns just the ID
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-456"}

        # Second call (GET) returns the full entry with nested structure
        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {
                "journal_entry": mock_phone_call_data,
                "can_edit": True
            },
            "cases": []
        }

        client.session.request.side_effect = [post_response, get_response]

        start_time = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 11, 10, 0, tzinfo=timezone.utc)

        entry = client.create_phone_call(
            description="Scam call",
            direction="inbound",
            start_time=start_time,
            end_time=end_time,
            identifiers=["phone:+1234567890"],
        )

        assert isinstance(entry, JournalEntry)
        assert entry.id == "entry-456"
        assert entry.type == "phone_call"
        assert client.session.request.call_count == 2  # POST + GET

    def test_create_in_progress_activity(self, client):
        """Test creating an in-progress activity."""
        from unittest.mock import Mock

        in_progress_data = {
            "id": "entry-in-progress",
            "type": "phone_call",
            "description": "Ongoing call",
            "start_time": "2025-01-15T12:00:00Z",
            "end_time": None,
            "details": {"direction": "inbound"},
        }

        # First call (POST) returns just the ID
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-in-progress"}

        # Second call (GET) returns the full entry with nested structure
        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {
                "journal_entry": in_progress_data,
                "can_edit": True
            },
            "cases": []
        }

        client.session.request.side_effect = [post_response, get_response]

        start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        # Even for in-progress, current signature requires end_time
        # The in_progress flag tells the backend to omit it
        end_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        entry = client.create_phone_call(
            description="Ongoing call",
            direction="inbound",
            start_time=start_time,
            end_time=end_time,
            in_progress=True,
        )

        assert entry.id == "entry-in-progress"
        assert entry.type == "phone_call"
        assert client.session.request.call_count == 2  # POST + GET


class TestScambusClientSearch:
    """Test search methods."""

    def test_search_identifiers(self, client, mock_identifier_data):
        """Test searching for identifiers."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        # Backend returns {data: [], nextCursor, hasMore} - NOT a plain list
        mock_response.json.return_value = {
            "data": [mock_identifier_data],
            "nextCursor": None,
            "hasMore": False
        }
        client.session.request.return_value = mock_response

        results = client.search_identifiers(query="scammer@example.com", types=["email"])

        # Verify the request was made correctly
        client.session.request.assert_called_once()
        call_args = client.session.request.call_args

        # Verify correct parameters were sent
        json_data = call_args.kwargs['json']
        assert json_data['searchQuery'] == "scammer@example.com"  # Backend expects searchQuery
        assert json_data['type'] == "email"  # Backend expects type (singular)
        assert 'types' not in json_data  # Backend doesn't accept types (plural)

        assert len(results) == 1
        assert isinstance(results[0], Identifier)
        assert results[0].display_value == "scammer@example.com"

    def test_search_identifiers_empty_results(self, client):
        """Test searching for identifiers with no results."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [],
            "nextCursor": None,
            "hasMore": False
        }
        client.session.request.return_value = mock_response

        results = client.search_identifiers(query="nonexistent")

        assert len(results) == 0
        assert isinstance(results, list)

    def test_search_cases(self, client, mock_case_data):
        """Test searching for cases."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        # API returns a plain list, not wrapped in results/total
        mock_response.json.return_value = [mock_case_data]
        client.session.request.return_value = mock_response

        results = client.search_cases(query="phishing", status="open")

        assert len(results) == 1
        assert isinstance(results[0], Case)
        assert results[0].title == "Phishing Campaign Investigation"


class TestScambusClientStreams:
    """Test stream methods."""

    def test_create_stream(self, client, mock_stream_data):
        """Test creating an export stream."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_stream_data
        client.session.request.return_value = mock_response

        stream = client.create_stream(
            name="Phone Scams Stream",
            data_type="journal_entry",
            identifier_types=["phone"],
            min_confidence=0.8,
        )

        assert isinstance(stream, ExportStream)
        assert stream.name == "Phone Scams Stream"
        assert stream.id == "stream-555"

    def test_list_streams(self, client, mock_stream_data):
        """Test listing export streams."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        # API returns data wrapped in {"data": [...], "pagination": {...}}
        mock_response.json.return_value = {"data": [mock_stream_data], "pagination": {}}
        client.session.request.return_value = mock_response

        result = client.list_streams()

        # list_streams returns a dict with 'data' and 'pagination'
        assert "data" in result
        assert len(result["data"]) == 1
        assert isinstance(result["data"][0], ExportStream)

    def test_consume_stream(self, client, mock_journal_entry_data):
        """Test consuming from a stream."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [mock_journal_entry_data],
            "cursor": "new-cursor",
        }
        client.session.request.return_value = mock_response

        # consume_stream returns the whole dict with events and cursor
        result = client.consume_stream("stream-555", limit=10)

        assert isinstance(result, dict)
        assert "events" in result
        assert "cursor" in result
        assert len(result["events"]) == 1
        assert result["cursor"] == "new-cursor"


class TestScambusClientErrorHandling:
    """Test error handling."""

    def test_authentication_error(self, client):
        """Test authentication error handling."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        client.session.request.return_value = mock_response

        with pytest.raises(ScambusAuthenticationError):
            client.create_detection(description="Test", identifiers=["email:test@example.com"])

    def test_validation_error(self, client):
        """Test validation error handling."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Validation failed",
            "details": {"field": "description is required"},
        }
        client.session.request.return_value = mock_response

        with pytest.raises(ScambusValidationError):
            client.create_detection(description="", identifiers=[])

    def test_not_found_error(self, client):
        """Test not found error handling."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Resource not found"}
        client.session.request.return_value = mock_response

        with pytest.raises(ScambusNotFoundError):
            client.get_case("nonexistent-case-id")

    def test_generic_api_error(self, client):
        """Test generic API error handling."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        client.session.request.return_value = mock_response

        with pytest.raises(ScambusAPIError):
            client.create_detection(description="Test", identifiers=["email:test@example.com"])


class TestIsTestFiltering:
    """Test that is_test filtering works correctly."""

    def test_query_journal_entries_excludes_test_by_default(self, client, mock_journal_entry_data):
        """Test that query_journal_entries excludes test data by default."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [mock_journal_entry_data],
            "nextCursor": None,
            "hasMore": False,
            "count": 1
        }
        client.session.request.return_value = mock_response

        client.query_journal_entries()

        # Verify the request was made without includeTest
        call_args = client.session.request.call_args
        json_data = call_args.kwargs.get('json')
        assert "includeTest" not in json_data

    def test_query_journal_entries_includes_test_when_specified(self, client, mock_journal_entry_data):
        """Test that query_journal_entries includes test data when include_test=True."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [mock_journal_entry_data],
            "nextCursor": None,
            "hasMore": False,
            "count": 1
        }
        client.session.request.return_value = mock_response

        client.query_journal_entries(include_test=True)

        # Verify the request was made with includeTest=True
        call_args = client.session.request.call_args
        json_data = call_args.kwargs.get('json')
        assert json_data.get("includeTest") is True

    def test_list_cases_excludes_test_by_default(self, client, mock_case_data):
        """Test that list_cases excludes test data by default."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [mock_case_data]}
        client.session.request.return_value = mock_response

        client.list_cases()

        # Verify the request was made without includeTest param
        call_args = client.session.request.call_args
        params = call_args.kwargs.get('params', {})
        assert "includeTest" not in params

    def test_list_cases_includes_test_when_specified(self, client, mock_case_data):
        """Test that list_cases includes test data when include_test=True."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [mock_case_data]}
        client.session.request.return_value = mock_response

        client.list_cases(include_test=True)

        # Verify the request was made with includeTest=true param
        call_args = client.session.request.call_args
        params = call_args.kwargs.get('params', {})
        assert params.get("includeTest") == "true"

    def test_search_identifiers_excludes_test_by_default(self, client, mock_identifier_data):
        """Test that search_identifiers excludes test data by default."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [mock_identifier_data],
            "nextCursor": None,
            "hasMore": False
        }
        client.session.request.return_value = mock_response

        client.search_identifiers(query="test")

        # Verify the request was made without includeTest
        call_args = client.session.request.call_args
        json_data = call_args.kwargs.get('json')
        assert "includeTest" not in json_data

    def test_search_identifiers_includes_test_when_specified(self, client, mock_identifier_data):
        """Test that search_identifiers includes test data when include_test=True."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [mock_identifier_data],
            "nextCursor": None,
            "hasMore": False
        }
        client.session.request.return_value = mock_response

        client.search_identifiers(query="test", include_test=True)

        # Verify the request was made with includeTest=True
        call_args = client.session.request.call_args
        json_data = call_args.kwargs.get('json')
        assert json_data.get("includeTest") is True

    def test_create_journal_entry_with_is_test(self, client, mock_journal_entry_data):
        """Test that create_journal_entry passes is_test flag correctly."""
        from unittest.mock import Mock

        # First call (POST) returns just the ID
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-test-123"}

        # Second call (GET) returns the full entry with is_test=True
        test_entry_data = dict(mock_journal_entry_data)
        test_entry_data["is_test"] = True
        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {
                "journal_entry": test_entry_data,
                "can_edit": True
            },
            "cases": []
        }

        client.session.request.side_effect = [post_response, get_response]

        entry = client.create_detection(
            description="Test detection",
            identifiers=["email:test@example.com"],
            is_test=True
        )

        # Verify the POST request included is_test
        post_call = client.session.request.call_args_list[0]
        json_data = post_call.kwargs.get('json')
        assert json_data.get("is_test") is True

    def test_create_case_with_is_test(self, client, mock_case_data):
        """Test that create_case passes is_test flag correctly."""
        from unittest.mock import Mock

        test_case_data = dict(mock_case_data)
        test_case_data["is_test"] = True

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = test_case_data
        client.session.request.return_value = mock_response

        case = client.create_case(title="Test Case", is_test=True)

        # Verify the POST request included is_test
        call_args = client.session.request.call_args
        json_data = call_args.kwargs.get('json')
        assert json_data.get("is_test") is True
