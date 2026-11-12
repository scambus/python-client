"""Admin methods for audit logs and journal processing events."""

import json
from typing import Any, Dict, Optional

from .exceptions import ScambusAPIError


def _present(params: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None}


def _audit_log_filter(
    originator_id: Optional[str],
    originator_type: Optional[str],
    org_id: Optional[str],
    method: Optional[str],
    path_prefix: Optional[str],
    status_code_min: Optional[int],
    status_code_max: Optional[int],
    permission_failures: bool,
    start_time: Optional[str],
    end_time: Optional[str],
) -> Dict[str, Any]:
    return _present(
        {
            "originatorId": originator_id,
            "originatorType": originator_type,
            "orgId": org_id,
            "method": method,
            "pathPrefix": path_prefix,
            "statusCodeMin": status_code_min,
            "statusCodeMax": status_code_max,
            "permissionFailures": "true" if permission_failures else None,
            "startTime": start_time,
            "endTime": end_time,
        }
    )


def _processing_event_filter(
    processor: Optional[str],
    result_state: Optional[str],
    result_path: Optional[str],
    result_value: Optional[str],
    result_contains: Optional[Dict[str, Any]],
    start_time: Optional[str],
    end_time: Optional[str],
    page: Optional[int],
    page_size: Optional[int],
) -> Dict[str, Any]:
    return _present(
        {
            "processor": processor,
            "resultState": result_state,
            "resultPath": result_path,
            "resultValue": result_value,
            "resultContains": None if result_contains is None else json.dumps(result_contains),
            "startTime": start_time,
            "endTime": end_time,
            "page": page,
            "page_size": page_size,
        }
    )


class AdminAuditMixin:
    """Audit administration for ScambusClient."""

    def list_audit_logs(
        self,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        originator_id: Optional[str] = None,
        originator_type: Optional[str] = None,
        org_id: Optional[str] = None,
        method: Optional[str] = None,
        path_prefix: Optional[str] = None,
        status_code_min: Optional[int] = None,
        status_code_max: Optional[int] = None,
        permission_failures: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List API request audit logs with filters and pagination."""
        params = _audit_log_filter(
            originator_id,
            originator_type,
            org_id,
            method,
            path_prefix,
            status_code_min,
            status_code_max,
            permission_failures,
            start_time,
            end_time,
        )
        params.update(_present({"page": page, "page_size": page_size}))
        return self._request("GET", "/admin/audit-logs", params=params)

    def get_audit_log(self, log_id: str) -> Dict[str, Any]:
        """Get one API request audit log by ID."""
        return self._request("GET", f"/admin/audit-logs/{log_id}")

    def get_audit_log_stats(self) -> Dict[str, Any]:
        """Get aggregate counts for API request audit logs."""
        return self._request("GET", "/admin/audit-logs/stats")

    def export_audit_logs(
        self,
        output_path: str,
        export_format: str = "json",
        max_records: Optional[int] = None,
        originator_id: Optional[str] = None,
        originator_type: Optional[str] = None,
        org_id: Optional[str] = None,
        method: Optional[str] = None,
        path_prefix: Optional[str] = None,
        status_code_min: Optional[int] = None,
        status_code_max: Optional[int] = None,
        permission_failures: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> None:
        """Stream API request audit logs as JSON or CSV to a local file."""
        params = _audit_log_filter(
            originator_id,
            originator_type,
            org_id,
            method,
            path_prefix,
            status_code_min,
            status_code_max,
            permission_failures,
            start_time,
            end_time,
        )
        params.update(_present({"format": export_format, "maxRecords": max_records}))
        with self._client.stream(
            "GET",
            f"{self.api_url}/admin/audit-logs/export",
            params=params,
            timeout=self.timeout,
        ) as response:
            if response.status_code >= 400:
                response.read()
                self._handle_error_response(response)
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        if export_format != "json":
            return
        # The server reports a mid-stream failure only as an "error" key after a 200 status.
        with open(output_path, encoding="utf-8") as f:
            try:
                body = json.load(f)
            except ValueError as exc:
                raise ScambusAPIError(f"Audit log export is not complete JSON: {exc}") from exc
        if "error" in body:
            raise ScambusAPIError(
                f"Audit log export failed after {body.get('count')} records: {body['error']}"
            )

    def list_journal_processing_events(
        self,
        journal_entry_id: Optional[str] = None,
        processor: Optional[str] = None,
        result_state: Optional[str] = None,
        result_path: Optional[str] = None,
        result_value: Optional[str] = None,
        result_contains: Optional[Dict[str, Any]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List journal entry processing events across the tenant with filters."""
        params = _processing_event_filter(
            processor,
            result_state,
            result_path,
            result_value,
            result_contains,
            start_time,
            end_time,
            page,
            page_size,
        )
        params.update(_present({"journalEntryId": journal_entry_id}))
        return self._request("GET", "/admin/journal-processing-events", params=params)

    def list_journal_entry_processing_events(
        self,
        journal_entry_id: str,
        processor: Optional[str] = None,
        result_state: Optional[str] = None,
        result_path: Optional[str] = None,
        result_value: Optional[str] = None,
        result_contains: Optional[Dict[str, Any]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List processing events for one journal entry."""
        params = _processing_event_filter(
            processor,
            result_state,
            result_path,
            result_value,
            result_contains,
            start_time,
            end_time,
            page,
            page_size,
        )
        return self._request(
            "GET", f"/journal-entries/{journal_entry_id}/processing-events", params=params
        )

    def get_user_activity(
        self,
        timeframe: Optional[str] = None,
        user_id: Optional[str] = None,
        originator_type: Optional[str] = None,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the latest 100 entity audit events with filters."""
        params = _present(
            {
                "timeframe": timeframe,
                "user_id": user_id,
                "originator_type": originator_type,
                "action_type": action_type,
                "entity_type": entity_type,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return self._request("GET", "/audit/user-activity", params=params)

    def get_audit_event(self, event_id: str) -> Dict[str, Any]:
        """Get one entity audit event by ID."""
        return self._request("GET", f"/audit/events/{event_id}")
