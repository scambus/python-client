"""Tests for audit administration methods."""

import json
from unittest.mock import MagicMock, Mock

import pytest

from scambus_client import ScambusAPIError
from scambus_client.exceptions import ScambusNotFoundError

API = "https://api.test.scambus.net/api"


def _respond(client, body):
    response = Mock()
    response.status_code = 200
    response.json.return_value = body
    client.session.request.return_value = response


def _call(client):
    kwargs = client.session.request.call_args.kwargs
    return kwargs["method"], kwargs["url"], kwargs["params"]


def _stream(client, status_code=200, chunks=(), error_body=None):
    response = Mock()
    response.status_code = status_code
    response.iter_bytes.return_value = list(chunks)
    response.json.return_value = error_body
    response.text = json.dumps(error_body)
    context = MagicMock()
    context.__enter__.return_value = response
    client._client.stream = Mock(return_value=context)
    return response


def test_list_audit_logs_sends_filters_and_pagination(client):
    _respond(client, {"logs": [], "total_count": 0, "page": 2, "page_size": 10, "has_more": False})

    result = client.list_audit_logs(
        page=2,
        page_size=10,
        originator_id="u-1",
        originator_type="user",
        org_id="o-1",
        method="POST",
        path_prefix="/api/cases",
        status_code_min=400,
        status_code_max=499,
        permission_failures=True,
        start_time="2026-11-01T00:00:00Z",
        end_time="2026-11-02T00:00:00Z",
    )

    assert result["page"] == 2
    assert _call(client) == (
        "GET",
        f"{API}/admin/audit-logs",
        {
            "originatorId": "u-1",
            "originatorType": "user",
            "orgId": "o-1",
            "method": "POST",
            "pathPrefix": "/api/cases",
            "statusCodeMin": 400,
            "statusCodeMax": 499,
            "permissionFailures": "true",
            "startTime": "2026-11-01T00:00:00Z",
            "endTime": "2026-11-02T00:00:00Z",
            "page": 2,
            "page_size": 10,
        },
    )


def test_list_audit_logs_omits_unset_filters(client):
    _respond(client, {"logs": []})

    client.list_audit_logs()

    assert _call(client) == ("GET", f"{API}/admin/audit-logs", {})


def test_get_audit_log(client):
    _respond(client, {"id": "log-1"})

    assert client.get_audit_log("log-1") == {"id": "log-1"}
    assert _call(client) == ("GET", f"{API}/admin/audit-logs/log-1", None)


def test_get_audit_log_stats(client):
    _respond(client, {"total_logs": 5})

    assert client.get_audit_log_stats() == {"total_logs": 5}
    assert _call(client) == ("GET", f"{API}/admin/audit-logs/stats", None)


def test_export_audit_logs_writes_csv(client, tmp_path):
    _stream(client, chunks=[b"ID,Method\n", b"1,GET\n"])
    output = tmp_path / "logs.csv"

    client.export_audit_logs(
        str(output), export_format="csv", max_records=500, method="GET", permission_failures=True
    )

    assert output.read_bytes() == b"ID,Method\n1,GET\n"
    args, kwargs = client._client.stream.call_args
    assert args == ("GET", f"{API}/admin/audit-logs/export")
    assert kwargs["params"] == {
        "method": "GET",
        "permissionFailures": "true",
        "format": "csv",
        "maxRecords": 500,
    }


def test_export_audit_logs_writes_json(client, tmp_path):
    _stream(client, chunks=[b'{"logs":[{"id":"1"}', b'],"count":1}'])
    output = tmp_path / "logs.json"

    client.export_audit_logs(str(output))

    assert json.loads(output.read_text()) == {"logs": [{"id": "1"}], "count": 1}
    assert client._client.stream.call_args.kwargs["params"] == {"format": "json"}


def test_export_audit_logs_raises_on_mid_stream_error(client, tmp_path):
    _stream(client, chunks=[b'{"logs":[{"id":"1"}],"count":1,"error":"stream failed"}'])

    with pytest.raises(ScambusAPIError, match="after 1 records: stream failed"):
        client.export_audit_logs(str(tmp_path / "logs.json"))


def test_export_audit_logs_raises_on_truncated_json(client, tmp_path):
    _stream(client, chunks=[b'{"logs":[{"id":"1"}'])

    with pytest.raises(ScambusAPIError, match="not complete JSON"):
        client.export_audit_logs(str(tmp_path / "logs.json"))


def test_export_audit_logs_raises_api_error_on_http_error(client, tmp_path):
    response = _stream(client, status_code=404, error_body={"error": "Not found"})
    output = tmp_path / "logs.json"

    with pytest.raises(ScambusNotFoundError, match="Not found"):
        client.export_audit_logs(str(output))

    response.read.assert_called_once()
    assert not output.exists()


def test_list_journal_processing_events_sends_filters(client):
    _respond(client, {"events": [], "total_count": 0})

    client.list_journal_processing_events(
        journal_entry_id="je-1",
        processor="conversation_identifier_extraction",
        result_state="failure",
        result_path="identifiers.0.type",
        result_value="phone",
        result_contains={"model": "gemini"},
        start_time="2026-11-01T00:00:00Z",
        end_time="2026-11-02T00:00:00Z",
        page=3,
        page_size=25,
    )

    assert _call(client) == (
        "GET",
        f"{API}/admin/journal-processing-events",
        {
            "processor": "conversation_identifier_extraction",
            "resultState": "failure",
            "resultPath": "identifiers.0.type",
            "resultValue": "phone",
            "resultContains": '{"model": "gemini"}',
            "startTime": "2026-11-01T00:00:00Z",
            "endTime": "2026-11-02T00:00:00Z",
            "page": 3,
            "page_size": 25,
            "journalEntryId": "je-1",
        },
    )


def test_list_journal_entry_processing_events(client):
    _respond(client, {"events": []})

    client.list_journal_entry_processing_events("je-1", result_state="success")

    assert _call(client) == (
        "GET",
        f"{API}/journal-entries/je-1/processing-events",
        {"resultState": "success"},
    )


def test_get_user_activity_sends_filters(client):
    _respond(client, {"events": [], "total": 0})

    client.get_user_activity(
        timeframe="7d",
        user_id="u-1",
        originator_type="user",
        action_type="deleted",
        entity_type="tag",
        start_date="2026-11-01T00:00:00Z",
        end_date="2026-11-02T00:00:00Z",
    )

    assert _call(client) == (
        "GET",
        f"{API}/audit/user-activity",
        {
            "timeframe": "7d",
            "user_id": "u-1",
            "originator_type": "user",
            "action_type": "deleted",
            "entity_type": "tag",
            "start_date": "2026-11-01T00:00:00Z",
            "end_date": "2026-11-02T00:00:00Z",
        },
    )


def test_get_audit_event(client):
    _respond(client, {"id": "ev-1"})

    assert client.get_audit_event("ev-1") == {"id": "ev-1"}
    assert _call(client) == ("GET", f"{API}/audit/events/ev-1", None)
