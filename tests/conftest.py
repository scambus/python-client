"""Shared pytest fixtures for scambus-client tests."""

from unittest.mock import Mock

import pytest

from scambus_client import ScambusClient


@pytest.fixture
def mock_api_key():
    """Return a mock API key."""
    return "test-api-key-12345"


@pytest.fixture
def mock_api_url():
    """Return a mock API URL."""
    return "https://api.test.scambus.net"


@pytest.fixture
def client(mock_api_url, mock_api_key):
    """Return a ScambusClient instance with mocked requests."""
    from unittest.mock import Mock

    # Create client with real session first
    client = ScambusClient(api_url=mock_api_url, api_token=mock_api_key)

    # Replace session with a mock that tests can configure
    mock_session = Mock()
    mock_session.headers = client.session.headers  # Keep the auth headers
    client.session = mock_session

    return client


@pytest.fixture
def mock_response():
    """Return a mock requests.Response object."""
    response = Mock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    return response


@pytest.fixture
def mock_journal_entry_data():
    """Return mock journal entry data."""
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
def mock_phone_call_data():
    """Return mock phone call journal entry data."""
    return {
        "id": "entry-456",
        "type": "phone_call",
        "description": "Scam call received",
        "performed_at": "2025-01-15T11:00:00Z",
        "start_time": "2025-01-15T11:00:00Z",
        "end_time": "2025-01-15T11:10:00Z",
        "details": {
            "direction": "inbound",
            "platform": "pstn",
            "duration": 600,
        },
        "identifiers": [
            {
                "id": "ident-456",
                "type": "phone",
                "value": "+1234567890",
                "displayValue": "+1 (234) 567-8900",
                "confidence": {"score": 0.90},
            }
        ],
        "created_at": "2025-01-15T11:00:00Z",
        "updated_at": "2025-01-15T11:00:00Z",
    }


@pytest.fixture
def mock_identifier_data():
    """Return mock identifier data."""
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
    """Return mock case data."""
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
    """Return mock export stream data."""
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


@pytest.fixture
def mock_tag_data():
    """Return mock tag data."""
    return {
        "id": "tag-999",
        "title": "High Priority",
        "tag_type": "valued",
        "description": "High priority items",
        "created_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_media_data():
    """Return mock media data."""
    return {
        "id": "media-777",
        "type": "s3",
        "fileName": "screenshot.png",
        "mimeType": "image/png",
        "fileSize": 12345,
        "uploadedAt": "2025-01-15T09:00:00Z",
        "notes": "Screenshot of phishing website",
    }
