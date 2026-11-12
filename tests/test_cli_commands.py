"""Unit tests for case, media, automation, identifier and stream CLI commands."""

import json
from datetime import datetime, timezone
from unittest.mock import Mock

from click.testing import CliRunner

from scambus_cli.cli import cli
from scambus_cli.commands.automations import automations
from scambus_cli.commands.cases import cases
from scambus_cli.commands.identifiers import identifiers
from scambus_cli.commands.media import media
from scambus_cli.commands.streams import streams
from scambus_client.models import Identifier, Media


class FakeContext:
    """CLI context with an injectable client."""

    def __init__(self, client):
        self.client = client

    def get_client(self):
        return self.client


def test_top_level_cli_registers_identifiers_group():
    result = CliRunner().invoke(cli, ["identifiers", "--help"])

    assert result.exit_code == 0
    assert "Browse identifiers" in result.output


def test_cases_delete_with_yes_deletes():
    client = Mock()
    result = CliRunner().invoke(cases, ["delete", "case-1", "--yes"], obj=FakeContext(client))

    assert result.exit_code == 0
    client.delete_case.assert_called_once_with("case-1")


def test_cases_delete_aborts_without_confirmation():
    client = Mock()
    result = CliRunner().invoke(cases, ["delete", "case-1"], input="n\n", obj=FakeContext(client))

    assert result.exit_code == 1
    client.delete_case.assert_not_called()


def test_media_get_json():
    client = Mock()
    client.get_media.return_value = Media(
        id="media-1", type="s3", file_name="a.png", mime_type="image/png", file_size=3, notes=None
    )
    result = CliRunner().invoke(media, ["get", "media-1", "--json"], obj=FakeContext(client))

    assert result.exit_code == 0
    assert json.loads(result.output)["file_name"] == "a.png"
    client.get_media.assert_called_once_with("media-1")


def test_automations_get_json():
    client = Mock()
    client.get_automation.return_value = {"id": "auto-1", "name": "Bot"}
    result = CliRunner().invoke(automations, ["get", "auto-1", "--json"], obj=FakeContext(client))

    assert result.exit_code == 0
    assert json.loads(result.output) == {"id": "auto-1", "name": "Bot"}


def test_identifiers_list_passes_filters_and_prints_json():
    client = Mock()
    client.list_identifiers.return_value = [
        Identifier(
            id="i-1",
            type="email",
            display_value="a@example.com",
            created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
    ]
    result = CliRunner().invoke(
        identifiers,
        ["list", "--type", "email", "--page", "2", "--limit", "50", "--json"],
        obj=FakeContext(client),
    )

    assert result.exit_code == 0
    client.list_identifiers.assert_called_once_with(identifier_type="email", page=2, limit=50)
    assert json.loads(result.output)[0]["display_value"] == "a@example.com"


def test_identifiers_get_reports_failure():
    client = Mock()
    client.get_identifier.side_effect = RuntimeError("boom")
    result = CliRunner().invoke(identifiers, ["get", "i-1"], obj=FakeContext(client))

    assert result.exit_code == 1
    assert "boom" in result.output


def test_streams_rebuild_with_yes():
    client = Mock()
    client.rebuild_stream.return_value = {"status": "started", "message": "Rebuild started"}
    result = CliRunner().invoke(streams, ["rebuild", "s-1", "--yes"], obj=FakeContext(client))

    assert result.exit_code == 0
    client.rebuild_stream.assert_called_once_with("s-1")


def test_rebuild_stream_posts_to_rebuild_route(client):
    response = Mock()
    response.status_code = 202
    response.json.return_value = {"status": "started"}
    client.session.request.return_value = response

    assert client.rebuild_stream("s-1") == {"status": "started"}
    call = client.session.request.call_args.kwargs
    assert call["method"] == "POST"
    assert call["url"].endswith("/export-streams/s-1/rebuild")
