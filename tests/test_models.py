"""Unit tests for Scambus models."""

from datetime import datetime, timezone

from scambus_client.models import (
    Case,
    ConversationMessage,
    DetectionDetails,
    EmailDetails,
    ExportStream,
    Identifier,
    JournalEntry,
    Media,
    PhoneCallDetails,
    Queue,
    QueueClusterIdentifier,
    QueueContactLog,
    QueueItem,
    QueueItemEvent,
    QueueStreamResponse,
    Tag,
)


class TestJournalEntry:
    """Test JournalEntry model."""

    def test_journal_entry_creation(self, mock_journal_entry_data):
        """Test creating a journal entry from data."""
        entry = JournalEntry.from_dict(mock_journal_entry_data)

        assert entry.id == "entry-123"
        assert entry.type == "detection"
        assert entry.description == "Test detection"
        assert isinstance(entry.details, dict)
        assert entry.details["category"] == "phishing"
        assert entry.details["confidence"] == 0.9

    def test_journal_entry_with_phone_call_details(self, mock_phone_call_data):
        """Test journal entry with phone call details."""
        entry = JournalEntry.from_dict(mock_phone_call_data)

        assert entry.type == "phone_call"
        assert isinstance(entry.details, dict)
        assert entry.details["direction"] == "inbound"
        assert entry.details["platform"] == "pstn"
        assert entry.details["duration"] == 600

    def test_journal_entry_in_progress(self):
        """Test in-progress journal entry (no end_time)."""
        data = {
            "id": "entry-in-progress",
            "type": "phone_call",
            "description": "Ongoing call",
            "startTime": "2025-01-15T12:00:00Z",
            "endTime": None,
            "details": {"direction": "inbound"},
        }
        entry = JournalEntry.from_dict(data)

        # Entry is in progress if it has start_time but no end_time
        assert entry.end_time is None
        assert entry.start_time is not None
        assert entry.id == "entry-in-progress"
        assert entry.type == "phone_call"


class TestDetectionDetails:
    """Test DetectionDetails model."""

    def test_detection_details_creation(self):
        """Test creating detection details."""
        details = DetectionDetails(
            data={"threat_type": "phishing"},
        )

        assert details.data == {"threat_type": "phishing"}
        assert details.category is None
        assert details.confidence is None

    def test_detection_details_to_dict(self):
        """Test converting detection details to dict."""
        details = DetectionDetails(
            data={"method": "url_analysis"},
        )
        data = details.to_dict()

        assert data["data"] == {"method": "url_analysis"}
        assert "category" not in data
        assert "confidence" not in data

    def test_detection_details_to_dict_fallback_from_details(self):
        """Test that deprecated 'details' field falls back to 'data' key in to_dict."""
        import warnings

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            det = DetectionDetails(
                details={"legacy_key": "value"},
            )
        data = det.to_dict()

        assert data["data"] == {"legacy_key": "value"}
        assert "details" not in data

    def test_detection_details_confidence_deprecation(self):
        """Test that setting confidence emits a deprecation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            DetectionDetails(confidence=0.85)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "IdentifierLookup" in str(w[0].message)

    def test_detection_details_category_deprecation(self):
        """Test that setting category emits a deprecation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            DetectionDetails(category="phishing")
            assert any(
                issubclass(warning.category, DeprecationWarning)
                and "category" in str(warning.message)
                for warning in w
            )

    def test_detection_details_details_deprecation(self):
        """Test that setting details emits a deprecation warning."""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            DetectionDetails(details={"key": "val"})
            assert any(
                issubclass(warning.category, DeprecationWarning)
                and "details" in str(warning.message).lower()
                for warning in w
            )


class TestPhoneCallDetails:
    """Test PhoneCallDetails model."""

    def test_phone_call_details_creation(self):
        """Test creating phone call details."""
        details = PhoneCallDetails(
            direction="inbound",
            recording_url="https://example.com/recording.mp3",
            transcript_url="https://example.com/transcript.txt",
        )

        assert details.direction == "inbound"
        assert details.recording_url == "https://example.com/recording.mp3"
        assert details.transcript_url == "https://example.com/transcript.txt"

    def test_phone_call_details_to_dict(self):
        """Test converting phone call details to dict."""
        details = PhoneCallDetails(direction="outbound")
        data = details.to_dict()

        assert data["direction"] == "outbound"
        assert "recordingUrl" in data or "recording_url" in data or data.get("recordingUrl") is None

    def test_phone_call_details_to_dict_with_structured_transcript(self):
        """Test converting structured phone call transcript messages."""
        details = PhoneCallDetails(
            direction="inbound",
            transcript=[
                ConversationMessage(
                    index=0,
                    message_id="call-msg-1",
                    timestamp=datetime(2025, 1, 15, 11, 1, tzinfo=timezone.utc),
                    body="Send the money today.",
                    is_outgoing=False,
                    platform_metadata={"is_transcription": True},
                )
            ],
        )

        data = details.to_dict()

        assert data["transcript"][0]["message_id"] == "call-msg-1"
        assert data["transcript"][0]["platform_metadata"]["is_transcription"] is True


class TestConversationMessage:
    """Test ConversationMessage model."""

    def test_conversation_message_phone_call_marker_round_trips(self):
        """Test phone call marker fields are serialized and parsed."""
        message = ConversationMessage(
            index=3,
            message_id="call-marker-entry-123",
            timestamp=datetime(2025, 1, 15, 11, 2, tzinfo=timezone.utc),
            body="Phone call",
            is_outgoing=False,
            message_type="phone_call_marker",
            phone_call_journal_entry_id="entry-123",
        )

        data = message.to_dict()
        parsed = ConversationMessage.from_dict(data)

        assert data["message_type"] == "phone_call_marker"
        assert data["phone_call_journal_entry_id"] == "entry-123"
        assert parsed.message_type == "phone_call_marker"
        assert parsed.phone_call_journal_entry_id == "entry-123"


class TestEmailDetails:
    """Test EmailDetails model."""

    def test_email_details_creation(self):
        """Test creating email details."""
        from datetime import datetime

        sent_at = datetime(2025, 1, 15, 10, 0, 0)
        details = EmailDetails(
            direction="inbound",
            subject="Phishing email",
            sent_at=sent_at,
            headers={"From": "scammer@example.com"},
            body="This is a phishing email",
        )

        assert details.subject == "Phishing email"
        assert details.direction == "inbound"
        assert details.sent_at == sent_at
        assert details.body == "This is a phishing email"


class TestIdentifier:
    """Test Identifier model."""

    def test_identifier_creation(self, mock_identifier_data):
        """Test creating an identifier from data."""
        identifier = Identifier.from_dict(mock_identifier_data)

        assert identifier.id == "ident-789"
        assert identifier.type == "email"
        assert identifier.display_value == "scammer@example.com"
        assert identifier.confidence == 0.85
        assert identifier.created_at is not None

    def test_identifier_attributes(self, mock_identifier_data):
        """Test identifier attributes."""
        identifier = Identifier.from_dict(mock_identifier_data)

        assert identifier.display_value == "scammer@example.com"
        assert identifier.updated_at is not None


class TestCase:
    """Test Case model."""

    def test_case_creation(self, mock_case_data):
        """Test creating a case from data."""
        case = Case.from_dict(mock_case_data)

        assert case.id == "case-321"
        assert case.title == "Phishing Campaign Investigation"
        assert case.status == "open"

    def test_case_timestamps(self, mock_case_data):
        """Test case timestamps."""
        case = Case.from_dict(mock_case_data)

        assert case.created_at is not None
        assert case.updated_at is not None


class TestExportStream:
    """Test ExportStream model."""

    def test_stream_creation(self, mock_stream_data):
        """Test creating an export stream from data."""
        stream = ExportStream.from_dict(mock_stream_data)

        assert stream.id == "stream-555"
        assert stream.name == "Phone Scams Stream"
        assert stream.data_type == "journal_entry"
        assert "phone" in stream.identifier_types
        assert stream.is_active is True

    def test_stream_filters(self, mock_stream_data):
        """Test stream filter settings."""
        stream = ExportStream.from_dict(mock_stream_data)

        assert stream.min_confidence == 0.8
        assert stream.max_confidence == 1.0


class TestQueueModels:
    """Test queue response models."""

    def test_queue_creation(self):
        """Test creating a queue from API data."""
        queue = Queue.from_dict(
            {
                "id": "queue-123",
                "name": "Initial contact",
                "description": "First-pass contact queue",
                "filter_criteria": {"identifier_type": "email"},
                "cadence_days": 3,
                "cooldown_hours": 12,
                "max_contacts_per_cluster": 2,
                "rotation_enabled": False,
                "priority_mode": "oldest_contact",
                "auto_populate": False,
                "actor_cluster_id": "cluster-actor",
                "actor_cluster_name": "Persona A",
                "redis_stream_key": "queues:queue-123:events",
                "stream_version": 7,
                "is_active": True,
                "is_test": False,
                "created_at": "2026-04-28T10:00:00Z",
                "updated_at": "2026-04-28T10:01:00Z",
            }
        )

        assert queue.id == "queue-123"
        assert queue.name == "Initial contact"
        assert queue.filter_criteria == {"identifier_type": "email"}
        assert queue.priority_mode == "oldest_contact"
        assert queue.redis_stream_key == "queues:queue-123:events"
        assert queue.created_at is not None

    def test_queue_item_creation(self):
        """Test creating a queue item from API data."""
        item = QueueItem.from_dict(
            {
                "id": "item-123",
                "queue_id": "queue-123",
                "cluster_id": "cluster-target",
                "representative_id": "identifier-123",
                "state": "claimed",
                "funnel_id": "funnel-123",
                "funnel_entry_id": "entry-123",
                "actor_cluster_id": "cluster-actor",
                "selected_channel": "email",
                "journey_state": {"queue_index": 0},
                "claimed_by": "worker-123",
                "claimed_at": "2026-04-28T10:02:00Z",
                "contact_count": 1,
                "next_contact_after": "2026-04-29T10:02:00Z",
                "priority": 42,
                "representative_value": "scammer@example.com",
                "representative_type": "email",
                "cluster_size": 3,
            }
        )

        assert item.id == "item-123"
        assert item.state == "claimed"
        assert item.journey_state == {"queue_index": 0}
        assert item.claimed_at is not None
        assert item.representative_value == "scammer@example.com"

    def test_queue_stream_response_creation(self):
        """Test creating a queue stream response from Redis event data."""
        response = QueueStreamResponse.from_dict(
            {
                "stream_key": "queues:queue-123:events",
                "cursor": "1714300000000-0",
                "claim_endpoint": "/api/queues/queue-123/claim",
                "source_of_truth": "postgres",
                "messages": [
                    {
                        "cursor": "1714300000000-0",
                        "event": "added",
                        "queue_id": "queue-123",
                        "queue_item_id": "item-123",
                        "cluster_id": "cluster-target",
                        "representative_id": "identifier-123",
                        "representative_type": "email",
                        "representative_value": "scammer@example.com",
                        "state": "pending",
                        "contact_count": 0,
                        "priority": 42,
                        "stream_version": 1,
                        "occurred_at": "2026-04-28T10:00:00Z",
                        "is_test": False,
                        "metadata": {"source": "queue"},
                    }
                ],
            }
        )

        assert response.stream_key == "queues:queue-123:events"
        assert response.cursor == "1714300000000-0"
        assert response.messages[0].event == "added"
        assert response.messages[0].occurred_at is not None
        assert response.messages[0].metadata == {"source": "queue"}

    def test_queue_history_event_and_identifier_models(self):
        """Test queue audit and cluster identifier models."""
        contact = QueueContactLog.from_dict(
            {
                "id": "contact-123",
                "queue_item_id": "item-123",
                "queue_id": "queue-123",
                "cluster_id": "cluster-target",
                "contacted_by": "worker-123",
                "outcome": "contacted",
                "contacted_at": "2026-04-28T10:05:00Z",
                "notes": "Sent first email",
            }
        )
        event = QueueItemEvent.from_dict(
            {
                "id": "event-123",
                "queue_item_id": "item-123",
                "queue_id": "queue-123",
                "target_queue_id": "queue-456",
                "cluster_id": "cluster-target",
                "representative_id": "identifier-123",
                "event": "moved_out",
                "state": "pending",
                "contact_count": 1,
                "priority": 42,
                "stream_version": 3,
                "metadata": {"reason": "manual_triage"},
                "occurred_at": "2026-04-28T10:06:00Z",
            }
        )
        identifier = QueueClusterIdentifier.from_dict(
            {
                "id": "identifier-123",
                "value": "scammer@example.com",
                "type": "email",
                "is_ours": False,
                "confidence": 0.92,
            }
        )

        assert contact.notes == "Sent first email"
        assert contact.contacted_at is not None
        assert event.event == "moved_out"
        assert event.target_queue_id == "queue-456"
        assert event.metadata == {"reason": "manual_triage"}
        assert identifier.confidence == 0.92


class TestMedia:
    """Test Media model."""

    def test_media_creation(self, mock_media_data):
        """Test creating media from data."""
        media = Media.from_dict(mock_media_data)

        assert media.id == "media-777"
        assert media.file_name == "screenshot.png"
        assert media.mime_type == "image/png"
        assert media.file_size == 12345

    def test_media_notes(self, mock_media_data):
        """Test media notes field."""
        media = Media.from_dict(mock_media_data)

        assert media.notes == "Screenshot of phishing website"


class TestTag:
    """Test Tag model."""

    def test_tag_creation(self, mock_tag_data):
        """Test creating a tag from data."""
        tag = Tag.from_dict(mock_tag_data)

        assert tag.id == "tag-999"
        assert tag.title == "High Priority"
        assert tag.tag_type == "valued"
        assert tag.description == "High priority items"
        assert tag.flow_up is True
        assert tag.flow_down is False
        assert tag.allow_dynamic_values is True
        assert tag.tag_values is not None
        assert len(tag.tag_values) == 1
        assert tag.tag_values[0].title == "Low"
