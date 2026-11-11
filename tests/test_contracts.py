"""Request and response shapes checked against the Go backend handlers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from click.testing import CliRunner

from scambus_cli.commands.automations import automations
from scambus_cli.commands.cases import cases
from scambus_client import AsyncScambusClient, ScambusAPIError, ScambusClient
from scambus_client.models import Case, ConversationMessage, Evidence, Media

WHEN = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
CASE = {"id": "case-1", "title": "Fraud", "status": "open"}


class FakeContext:
    def __init__(self, client):
        self.client = client

    def get_client(self):
        return self.client


@pytest.fixture
def sync_client():
    client = ScambusClient(api_url="https://api.test", api_token="t")
    client._request = Mock()
    client.get_journal_entry = Mock(return_value=Mock())
    return client


@pytest.fixture
def async_client():
    client = AsyncScambusClient(api_url="https://api.test", api_token="t")
    client._request = AsyncMock()
    client.get_journal_entry = AsyncMock(return_value=Mock())
    return client


async def _call(client, name, *args, **kwargs):
    result = getattr(client, name)(*args, **kwargs)
    if isinstance(client, AsyncScambusClient):
        result = await result
    return result


@pytest.fixture(params=["sync", "async"])
def any_client(request, sync_client, async_client):
    return sync_client if request.param == "sync" else async_client


def _body(client):
    return client._request.call_args.kwargs["json_data"]


def _media(media_id):
    return Media(id=media_id, type="s3", file_name="a.png", mime_type="image/png", file_size=1)


@pytest.mark.asyncio
async def test_search_cases_sends_backend_fields_and_reads_data(any_client):
    any_client._request.return_value = {"data": [CASE], "hasMore": False}

    results = await _call(any_client, "search_cases", query="fraud", status="open", limit=5)

    assert _body(any_client) == {"limit": 5, "searchQuery": "fraud", "status": ["open"]}
    assert [c.id for c in results] == ["case-1"]
    assert isinstance(results[0], Case)


@pytest.mark.asyncio
async def test_search_cases_raises_on_unexpected_shape(any_client):
    any_client._request.return_value = [CASE]

    with pytest.raises(ScambusAPIError, match="from POST /search/cases"):
        await _call(any_client, "search_cases", query="fraud")


@pytest.mark.asyncio
async def test_list_automations_returns_page_data(any_client):
    any_client._request.return_value = {
        "data": [{"id": "a-1"}],
        "pagination": {"page": 1, "page_size": 100, "total_items": 1, "total_pages": 1},
    }

    assert await _call(any_client, "list_automations") == [{"id": "a-1"}]


@pytest.mark.asyncio
async def test_list_automations_reads_every_page(any_client):
    any_client._request.side_effect = [
        {"data": [{"id": "a-1"}], "pagination": {"page": 1, "total_pages": 2}},
        {"data": [{"id": "a-2"}], "pagination": {"page": 2, "total_pages": 2}},
    ]

    assert await _call(any_client, "list_automations") == [{"id": "a-1"}, {"id": "a-2"}]
    assert [c.kwargs["params"]["page"] for c in any_client._request.call_args_list] == [1, 2]


@pytest.mark.asyncio
async def test_list_automations_raises_on_unexpected_shape(any_client):
    any_client._request.return_value = {"error": "nope"}

    with pytest.raises(ScambusAPIError):
        await _call(any_client, "list_automations")


@pytest.mark.asyncio
async def test_create_automation_api_key_sends_expires_at(any_client):
    any_client._request.return_value = {"id": "k-1", "key": "s", "secret_id": "k-1"}

    await _call(
        any_client, "create_automation_api_key", "a-1", "Key", expires_at="2027-01-01T00:00:00Z"
    )

    assert _body(any_client) == {"name": "Key", "expires_at": "2027-01-01T00:00:00Z"}


@pytest.mark.asyncio
async def test_create_automation_sends_only_fields_backend_reads(any_client):
    any_client._request.return_value = {"id": "a-1"}

    await _call(any_client, "create_automation", "Bot", description="d")

    assert _body(any_client) == {"name": "Bot", "description": "d"}


@pytest.mark.asyncio
async def test_create_journal_entry_accepts_evidence_model(any_client):
    any_client._request.return_value = {"id": "je-1"}
    evidence = Evidence(type="screenshot", media_id="m-1", source="web", collected_at=WHEN)

    await _call(any_client, "create_journal_entry", "note", "d", evidence=evidence)

    assert _body(any_client)["evidence"] == {
        "type": "screenshot",
        "source": "web",
        "collected_at": "2026-01-02T03:04:05+00:00",
        "media_id": "m-1",
    }


def test_evidence_from_dict_reads_backend_response():
    evidence = Evidence.from_dict(
        {"id": "e-1", "type": "image", "media_id": "m-1", "collected_at": "2026-01-02T03:04:05Z"}
    )

    assert evidence.media_id == "m-1"
    assert evidence.collected_at == WHEN


HELPERS = {
    "create_detection": lambda: {"description": "d"},
    "create_phone_call": lambda: {
        "description": "d",
        "direction": "inbound",
        "start_time": WHEN,
        "end_time": WHEN,
    },
    "create_email": lambda: {
        "description": "d",
        "direction": "inbound",
        "subject": "s",
        "sent_at": WHEN,
    },
    "create_text_conversation": lambda: {
        "description": "d",
        "platform": "sms",
        "start_time": WHEN,
        "end_time": WHEN,
    },
    "create_conversation_continuation": lambda: {
        "parent_entry": "je-parent",
        "messages": [
            ConversationMessage(
                index=0, message_id="m", timestamp=WHEN, body="hi", is_outgoing=False
            )
        ],
    },
    "create_note": lambda: {"description": "d"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("helper", sorted(HELPERS))
async def test_helpers_send_one_evidence_per_media(any_client, helper):
    any_client._request.return_value = {"id": "je-1"}

    await _call(any_client, helper, media=[_media("m-1"), _media("m-2")], **HELPERS[helper]())

    evidence = _body(any_client)["evidence"]
    assert [e["media_id"] for e in evidence] == ["m-1", "m-2"]
    for item in evidence:
        assert not {"media_ids", "collectedAt", "title"} & item.keys()


@pytest.mark.asyncio
@pytest.mark.parametrize("helper", sorted(HELPERS))
async def test_helpers_merge_media_into_given_evidence(any_client, helper):
    any_client._request.return_value = {"id": "je-1"}
    given = Evidence(type="document", media_id="m-0", collected_at=WHEN)

    await _call(any_client, helper, media=_media("m-1"), evidence=given, **HELPERS[helper]())

    evidence = _body(any_client)["evidence"]
    assert [(e["type"], e["media_id"]) for e in evidence] == [
        ("document", "m-0"),
        ("document", "m-1"),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "helper", ["create_email", "create_text_conversation", "create_conversation_continuation"]
)
async def test_helpers_send_collected_at(any_client, helper):
    any_client._request.return_value = {"id": "je-1"}

    await _call(any_client, helper, media=_media("m-1"), **HELPERS[helper]())

    assert _body(any_client)["evidence"][0]["collected_at"] == "2026-01-02T03:04:05+00:00"


@pytest.mark.asyncio
@pytest.mark.parametrize("response,expected", [([{"tag_id": "t"}], [{"tag_id": "t"}]), (None, [])])
async def test_get_effective_tags_reads_bare_list_or_null(any_client, response, expected):
    any_client._request.return_value = response

    assert await _call(any_client, "get_effective_tags", "identifier", "i-1") == expected


@pytest.mark.asyncio
async def test_get_effective_tags_raises_on_unexpected_shape(any_client):
    any_client._request.return_value = {"error": "nope"}

    with pytest.raises(ScambusAPIError):
        await _call(any_client, "get_effective_tags", "identifier", "i-1")


@pytest.mark.asyncio
async def test_get_identifier_tag_history_reads_entries(any_client):
    any_client._request.return_value = {
        "entries": [{"id": "je-1", "type": "tag_operation", "description": "d"}]
    }

    entries = await _call(any_client, "get_identifier_tag_history", "i-1")

    assert any_client._request.call_args.args == ("GET", "/identifiers/i-1/tag-history")
    assert [(e.id, e.type) for e in entries] == [("je-1", "tag_operation")]


@pytest.mark.parametrize("args,expected", [(["--json"], '"notes": "n"'), ([], "Notes")])
def test_cli_cases_get_shows_notes(args, expected):
    client = Mock()
    client.get_case.return_value = Case(id="c-1", title="t", notes="n", status="open")

    result = CliRunner().invoke(cases, ["get", "c-1", *args], obj=FakeContext(client))

    assert result.exit_code == 0, result.output
    assert expected in result.output


def test_cli_create_key_combines_secret_id_and_key():
    client = Mock()
    client.get_automation.return_value = {"name": "Bot"}
    client.create_automation_api_key.return_value = {"id": "k-1", "secret_id": "k-1", "key": "sec"}

    result = CliRunner().invoke(
        automations,
        ["create-key", "00000000-0000-0000-0000-000000000001", "--json"],
        obj=FakeContext(client),
    )

    assert result.exit_code == 0, result.output
    assert '"combined_key": "k-1:sec"' in result.output


def test_cli_list_reads_is_active():
    client = Mock()
    client.list_automations.return_value = [
        {"id": "a-1", "name": "Bot", "is_active": True, "created_at": "2026-01-02T00:00:00Z"}
    ]

    result = CliRunner().invoke(automations, ["list"], obj=FakeContext(client))

    assert result.exit_code == 0, result.output
    assert "Yes" in result.output


def test_cli_list_keys_reports_revoked_from_is_active():
    client = Mock()
    client.list_automation_api_keys.return_value = [
        {"id": "k-1", "name": "Old", "is_active": False, "created_at": "2026-01-02T00:00:00Z"}
    ]

    result = CliRunner().invoke(automations, ["list-keys", "a-1"], obj=FakeContext(client))

    assert result.exit_code == 0, result.output
    assert "Yes" in result.output
