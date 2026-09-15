"""Unit tests for AsyncScambusClient."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from scambus_client import (
    AsyncScambusClient,
    ScambusAPIError,
    ScambusAuthenticationError,
    ScambusNotFoundError,
)
from scambus_client.models import (
    Case,
    ExportStream,
    Identifier,
    JournalEntry,
    QueueItem,
    QueueStreamResponse,
)


@pytest_asyncio.fixture
async def async_client(mock_api_url, mock_api_key):
    """Return an AsyncScambusClient instance with mocked HTTP client."""
    client = AsyncScambusClient(api_url=mock_api_url, api_token=mock_api_key)

    # Replace _client with a mock
    mock_http_client = AsyncMock()
    mock_http_client.headers = dict(client._auth_headers)
    client._client = mock_http_client

    yield client


@pytest.fixture
def mock_api_key():
    return "test-api-key-12345"


@pytest.fixture
def mock_api_url():
    return "https://api.test.scambus.net"


@pytest.fixture
def mock_journal_entry_data():
    return {
        "id": "entry-123",
        "type": "detection",
        "description": "Test detection",
        "performed_at": "2025-01-15T10:00:00Z",
        "start_time": "2025-01-15T10:00:00Z",
        "end_time": "2025-01-15T10:05:00Z",
        "details": {
            "category": "phishing",
            "confidence": 0.9,
            "source": "automated",
        },
        "identifiers": [
            {
                "id": "ident-123",
                "type": "email",
                "value": "scammer@example.com",
                "displayValue": "scammer@example.com",
                "confidence": {"score": 0.85},
            }
        ],
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def mock_identifier_data():
    return {
        "id": "ident-789",
        "type": "email",
        "value": "scammer@example.com",
        "displayValue": "scammer@example.com",
        "confidence": {"score": 0.85},
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-15T12:00:00Z",
    }


@pytest.fixture
def mock_case_data():
    return {
        "id": "case-321",
        "title": "Phishing Campaign Investigation",
        "notes": "Investigating coordinated phishing campaign",
        "status": "open",
        "createdAt": "2025-01-10T00:00:00Z",
        "updatedAt": "2025-01-15T00:00:00Z",
        "createdBy": "user-123",
    }


@pytest.fixture
def mock_stream_data():
    return {
        "id": "stream-555",
        "name": "Phone Scams Stream",
        "dataType": "journal_entry",
        "identifierTypes": ["phone"],
        "minConfidence": 0.8,
        "maxConfidence": 1.0,
        "isActive": True,
        "createdAt": "2025-01-14T00:00:00Z",
        "updatedAt": "2025-01-14T00:00:00Z",
    }


class TestAsyncScambusClientInit:
    """Test AsyncScambusClient initialization."""

    def test_init_with_credentials(self, mock_api_url, mock_api_key):
        """Test client initialization with API token."""
        client = AsyncScambusClient(api_url=mock_api_url, api_token=mock_api_key)
        assert client.api_url == f"{mock_api_url}/api"
        assert client._client is not None
        assert "Authorization" in client._auth_headers

    def test_init_without_api_key(self, mock_api_url, monkeypatch):
        """Test client initialization without API key raises ValueError."""
        monkeypatch.setattr(
            "scambus_client._base_client.get_api_token", lambda api_token=None: None
        )
        monkeypatch.setattr(
            "scambus_client._base_client.get_api_key_id", lambda api_key_id=None: None
        )
        monkeypatch.setattr(
            "scambus_client._base_client.get_api_key_secret",
            lambda api_key_secret=None: None,
        )
        with pytest.raises(ValueError, match="No authentication provided"):
            AsyncScambusClient(api_url=mock_api_url)


class TestAsyncScambusClientJournalEntries:
    """Test journal entry methods."""

    @pytest.mark.asyncio
    async def test_create_detection(self, async_client, mock_journal_entry_data):
        """Test creating a detection journal entry."""
        # First call (POST) returns just the ID
        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-123"}

        # Second call (GET) returns the full entry
        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {"journal_entry": mock_journal_entry_data, "can_edit": True},
            "cases": [],
        }

        async_client._client.request.side_effect = [post_response, get_response]

        entry = await async_client.create_detection(
            description="Test detection",
            identifiers=["email:scammer@example.com"],
            details={"data": {"threat_type": "phishing"}},
        )

        assert isinstance(entry, JournalEntry)
        assert entry.id == "entry-123"
        assert entry.type == "detection"
        assert async_client._client.request.call_count == 2  # POST + GET

    @pytest.mark.asyncio
    async def test_create_phone_call(self, async_client):
        """Test creating a phone call journal entry."""
        phone_data = {
            "id": "entry-456",
            "type": "phone_call",
            "description": "Scam call received",
            "performed_at": "2025-01-15T11:00:00Z",
            "start_time": "2025-01-15T11:00:00Z",
            "end_time": "2025-01-15T11:10:00Z",
            "details": {"direction": "inbound"},
        }

        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-456"}

        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {"journal_entry": phone_data, "can_edit": True},
            "cases": [],
        }

        async_client._client.request.side_effect = [post_response, get_response]

        start_time = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 11, 10, 0, tzinfo=timezone.utc)

        entry = await async_client.create_phone_call(
            description="Scam call",
            direction="inbound",
            start_time=start_time,
            end_time=end_time,
            identifiers=["phone:+1234567890"],
        )

        assert isinstance(entry, JournalEntry)
        assert entry.id == "entry-456"
        assert entry.type == "phone_call"

    @pytest.mark.asyncio
    async def test_create_phone_call_with_transcript_enables_ai_extract(self, async_client):
        """Test structured phone call transcripts are sent for extraction."""
        phone_data = {
            "id": "entry-456",
            "type": "phone_call",
            "description": "Scam call received",
            "performed_at": "2025-01-15T11:00:00Z",
            "start_time": "2025-01-15T11:00:00Z",
            "end_time": "2025-01-15T11:10:00Z",
            "details": {"direction": "inbound"},
        }

        post_response = Mock()
        post_response.status_code = 201
        post_response.json.return_value = {"id": "entry-456"}

        get_response = Mock()
        get_response.status_code = 200
        get_response.json.return_value = {
            "journal_entry": {"journal_entry": phone_data, "can_edit": True},
            "cases": [],
        }

        async_client._client.request.side_effect = [post_response, get_response]

        start_time = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 11, 10, 0, tzinfo=timezone.utc)

        await async_client.create_phone_call(
            description="Scam call",
            direction="inbound",
            start_time=start_time,
            end_time=end_time,
            transcript=[
                {
                    "index": 0,
                    "message_id": "call-msg-1",
                    "timestamp": "2025-01-15T11:01:00Z",
                    "body": "Send the money today.",
                    "is_outgoing": False,
                    "platform_metadata": {"is_transcription": True},
                }
            ],
        )

        payload = async_client._client.request.call_args_list[0].kwargs["json"]

        assert payload["ai_extract"] is True
        assert payload["details"]["transcript"][0]["message_id"] == "call-msg-1"
        assert payload["details"]["transcript"][0]["platform_metadata"] == {
            "is_transcription": True
        }


class TestAsyncScambusClientSearch:
    """Test search methods."""

    @pytest.mark.asyncio
    async def test_search_identifiers(self, async_client, mock_identifier_data):
        """Test searching for identifiers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [mock_identifier_data],
            "nextCursor": None,
            "hasMore": False,
        }
        async_client._client.request.return_value = mock_response

        results = await async_client.search_identifiers(
            query="scammer@example.com", types=["email"]
        )

        assert len(results["data"]) == 1
        assert isinstance(results["data"][0], Identifier)
        assert results["data"][0].display_value == "scammer@example.com"

    @pytest.mark.asyncio
    async def test_search_cases(self, async_client, mock_case_data):
        """Test searching for cases."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [mock_case_data]
        async_client._client.request.return_value = mock_response

        results = await async_client.search_cases(query="phishing", status="open")

        assert len(results) == 1
        assert isinstance(results[0], Case)
        assert results[0].title == "Phishing Campaign Investigation"


class TestAsyncScambusClientStreams:
    """Test stream methods."""

    @pytest.mark.asyncio
    async def test_create_stream(self, async_client, mock_stream_data):
        """Test creating an export stream."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_stream_data
        async_client._client.request.return_value = mock_response

        stream = await async_client.create_stream(
            name="Phone Scams Stream",
            data_type="journal_entry",
            identifier_types=["phone"],
            min_confidence=0.8,
        )

        assert isinstance(stream, ExportStream)
        assert stream.name == "Phone Scams Stream"
        assert stream.id == "stream-555"

    @pytest.mark.asyncio
    async def test_consume_stream(self, async_client, mock_journal_entry_data):
        """Test consuming from a stream."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [mock_journal_entry_data],
            "next_cursor": "new-cursor",
            "has_more": False,
        }
        async_client._client.request.return_value = mock_response

        result = await async_client.consume_stream("stream-555", limit=10)

        assert isinstance(result, dict)
        assert "messages" in result
        assert "next_cursor" in result
        assert len(result["messages"]) == 1
        assert result["next_cursor"] == "new-cursor"


class TestAsyncScambusClientQueues:
    """Test async queue methods."""

    @pytest.mark.asyncio
    async def test_read_queue_stream(self, async_client):
        """Test reading queue Redis stream events."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stream_key": "queues:queue-123:events",
            "cursor": "1714300000000-0",
            "claim_endpoint": "/api/queues/queue-123/claim",
            "source_of_truth": "postgres",
            "messages": [
                {
                    "cursor": "1714300000000-0",
                    "event": "claimed",
                    "queue_id": "queue-123",
                    "queue_item_id": "item-123",
                    "cluster_id": "cluster-target",
                    "representative_id": "identifier-123",
                    "state": "claimed",
                    "contact_count": 0,
                    "priority": 42,
                    "stream_version": 2,
                    "occurred_at": "2026-04-28T10:00:00Z",
                    "is_test": False,
                }
            ],
        }
        async_client._client.request.return_value = mock_response

        result = await async_client.read_queue_stream(
            "queue-123", cursor="$", limit=1, block_ms=1000
        )

        assert isinstance(result, QueueStreamResponse)
        assert result.messages[0].event == "claimed"
        assert async_client._client.request.call_args.kwargs["params"] == {
            "cursor": "$",
            "limit": 1,
            "block_ms": 1000,
        }

    @pytest.mark.asyncio
    async def test_claim_queue_item(self, async_client):
        """Test claiming a queue item."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "item-123",
            "queue_id": "queue-123",
            "cluster_id": "cluster-target",
            "representative_id": "identifier-123",
            "state": "claimed",
        }
        async_client._client.request.return_value = mock_response

        item = await async_client.claim_queue_item("queue-123")

        assert isinstance(item, QueueItem)
        assert item.state == "claimed"
        assert async_client._client.request.call_args.kwargs["url"].endswith(
            "/queues/queue-123/claim"
        )


class TestAsyncScambusClientErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_authentication_error(self, async_client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.text = "Invalid API key"
        async_client._client.request.return_value = mock_response

        with pytest.raises(ScambusAuthenticationError):
            await async_client.create_detection(
                description="Test", identifiers=["email:test@example.com"]
            )

    @pytest.mark.asyncio
    async def test_not_found_error(self, async_client):
        """Test not found error handling."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Resource not found"}
        mock_response.text = "Resource not found"
        async_client._client.request.return_value = mock_response

        with pytest.raises(ScambusNotFoundError):
            await async_client.get_case("nonexistent-case-id")

    @pytest.mark.asyncio
    async def test_server_error_no_retry(self, async_client):
        """Test server error with retries disabled."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_response.text = "Internal server error"
        async_client._client.request.return_value = mock_response
        async_client.max_retries = 0

        with pytest.raises(ScambusAPIError):
            await async_client.create_detection(
                description="Test", identifiers=["email:test@example.com"]
            )


class TestAsyncContextManager:
    """Test async context manager support."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_api_url, mock_api_key):
        """Test that AsyncScambusClient works as an async context manager."""
        async with AsyncScambusClient(api_url=mock_api_url, api_token=mock_api_key) as client:
            assert client is not None
            assert client.api_url == f"{mock_api_url}/api"
