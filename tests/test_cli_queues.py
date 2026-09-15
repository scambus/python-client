"""Unit tests for queue CLI commands."""

from click.testing import CliRunner

from scambus_cli.cli import cli
from scambus_cli.commands.queues import queues
from scambus_client.models import Queue, QueueItem, QueueStreamMessage, QueueStreamResponse


class FakeContext:
    """CLI context with an injectable client."""

    def __init__(self, client):
        self.client = client

    def get_client(self):
        return self.client


class FakeQueueClient:
    """Small fake client for queue command tests."""

    def __init__(self):
        self.created_queue = None

    def list_queues(self):
        return [
            Queue(
                id="queue-123",
                name="Initial contact",
                priority_mode="fifo",
                redis_stream_key="queues:queue-123:events",
            )
        ]

    def create_queue(self, **kwargs):
        self.created_queue = kwargs
        return Queue(
            id="queue-456",
            name=kwargs["name"],
            filter_criteria=kwargs.get("filter_criteria") or {},
            priority_mode=kwargs.get("priority_mode") or "fifo",
        )

    def claim_queue_item(self, queue_id):
        return QueueItem(
            id="item-123",
            queue_id=queue_id,
            cluster_id="cluster-target",
            representative_id="identifier-123",
            state="claimed",
            representative_value="scammer@example.com",
            representative_type="email",
        )

    def read_queue_stream(self, queue_id, cursor="0", limit=None, block_ms=None):
        return QueueStreamResponse(
            stream_key=f"queues:{queue_id}:events",
            cursor="1714300000000-0",
            claim_endpoint=f"/api/queues/{queue_id}/claim",
            source_of_truth="postgres",
            messages=[
                QueueStreamMessage(
                    cursor="1714300000000-0",
                    event="added",
                    queue_id=queue_id,
                    queue_item_id="item-123",
                    cluster_id="cluster-target",
                    representative_id="identifier-123",
                    state="pending",
                    contact_count=0,
                    priority=42,
                    stream_version=1,
                    occurred_at=None,
                    is_test=False,
                )
            ],
        )


def test_top_level_cli_registers_queues_group():
    """Test the top-level CLI exposes queue commands."""
    result = CliRunner().invoke(cli, ["queues", "--help"])

    assert result.exit_code == 0
    assert "Manage and consume work queues" in result.output


def test_queues_list_json():
    """Test listing queues as JSON."""
    client = FakeQueueClient()
    result = CliRunner().invoke(queues, ["list", "--json"], obj=FakeContext(client))

    assert result.exit_code == 0
    assert '"id": "queue-123"' in result.output
    assert '"redis_stream_key": "queues:queue-123:events"' in result.output


def test_queues_create_parses_filter_json():
    """Test queue creation passes parsed settings to the client."""
    client = FakeQueueClient()
    result = CliRunner().invoke(
        queues,
        [
            "create",
            "--name",
            "Phone follow-up",
            "--filter-json",
            '{"identifier_type":"phone"}',
            "--priority-mode",
            "oldest_contact",
            "--manual",
            "--json",
        ],
        obj=FakeContext(client),
    )

    assert result.exit_code == 0
    assert client.created_queue["filter_criteria"] == {"identifier_type": "phone"}
    assert client.created_queue["priority_mode"] == "oldest_contact"
    assert client.created_queue["auto_populate"] is False
    assert '"id": "queue-456"' in result.output


def test_queues_claim_json():
    """Test claiming a queue item as JSON."""
    client = FakeQueueClient()
    result = CliRunner().invoke(queues, ["claim", "queue-123", "--json"], obj=FakeContext(client))

    assert result.exit_code == 0
    assert '"id": "item-123"' in result.output
    assert '"state": "claimed"' in result.output


def test_queues_stream_json():
    """Test reading queue stream events as JSON."""
    client = FakeQueueClient()
    result = CliRunner().invoke(
        queues,
        ["stream", "queue-123", "--cursor", "$", "--limit", "1", "--json"],
        obj=FakeContext(client),
    )

    assert result.exit_code == 0
    assert '"source_of_truth": "postgres"' in result.output
    assert '"event": "added"' in result.output
