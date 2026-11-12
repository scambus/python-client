"""Admin methods for maintenance jobs, reprocess jobs and the task queue."""

from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

MAINTENANCE_JOBS = (
    "rebuild-identifier-tags",
    "rebuild-graph-edges",
    "rebuild-network-sizes",
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-media-thumbnails",
    "backfill-media-transcripts",
    "backfill-tranco-checks",
    "backfill-scam-confidence-scope",
)

MAINTENANCE_RESET_JOBS = (
    "rebuild-identifier-tags",
    "rebuild-graph-edges",
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-tranco-checks",
)

MAINTENANCE_FORCE_JOBS = ("backfill-cluster-member-contexts",)

MAINTENANCE_PROGRESS_JOBS = (
    "rebuild-identifier-tags",
    "rebuild-graph-edges",
    "rebuild-network-sizes",
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-tranco-checks",
)

MAINTENANCE_MISSING_COUNT_JOBS = (
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-media-thumbnails",
    "backfill-media-transcripts",
    "backfill-tranco-checks",
)

REPROCESS_JOBS = ("enrichment-reprocess", "extraction-reprocess", "nsfw-scan")

TASK_STATES = ("pending", "active", "scheduled", "retry", "archived", "completed")

Response = Union[Dict[str, Any], List[Any]]


def _require(value: str, known: tuple, kind: str) -> None:
    if value not in known:
        raise ValueError(f"unknown {kind} {value!r}; expected one of: {', '.join(known)}")


def _queue_path(queue: str) -> str:
    return f"/admin/task-queue/queues/{quote(queue, safe='')}"


def _without_none(fields: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


class AdminJobsMixin:
    """Background job administration for ScambusClient."""

    def start_maintenance_job(
        self, name: str, reset: bool = False, force: bool = False
    ) -> Response:
        """Start the maintenance job NAME, optionally from a fresh checkpoint or with force."""
        _require(name, MAINTENANCE_JOBS, "maintenance job")
        params = {}
        if reset:
            _require(name, MAINTENANCE_RESET_JOBS, "resettable maintenance job")
            params["reset"] = "true"
        if force:
            _require(name, MAINTENANCE_FORCE_JOBS, "forceable maintenance job")
            params["force"] = "true"
        return self._request("POST", f"/admin/maintenance/{name}", params=params or None)

    def get_maintenance_progress(self, name: str) -> Response:
        """Get the checkpoint progress of the maintenance job NAME."""
        _require(name, MAINTENANCE_PROGRESS_JOBS, "maintenance job with progress")
        return self._request("GET", f"/admin/maintenance/{name}/progress")

    def get_maintenance_missing_count(self, name: str) -> Response:
        """Count the rows that the maintenance job NAME has still to process."""
        _require(name, MAINTENANCE_MISSING_COUNT_JOBS, "maintenance job with a missing count")
        subject = name[len("backfill-") :]
        return self._request("GET", f"/admin/maintenance/missing-{subject}-count")

    def start_scam_tag_cleanup(self, dry_run: bool = False) -> Response:
        """Start a scam tag cleanup run; a dry run only counts the stale tag values."""
        params = {"dry_run": "true"} if dry_run else None
        return self._request("POST", "/admin/maintenance/scam-tag-cleanup", params=params)

    def get_scam_tag_cleanup(self) -> Response:
        """Get the report of the newest scam tag cleanup run."""
        return self._request("GET", "/admin/maintenance/scam-tag-cleanup")

    def reset_failed_media_vision(self) -> Response:
        """Move every failed media vision row back to pending."""
        return self._request("POST", "/admin/maintenance/reset-failed-media-vision")

    def get_embedding_usage(self) -> Response:
        """Get the Gemini embedding usage for the last hour."""
        return self._request("GET", "/admin/maintenance/embedding-usage")

    def get_opensanctions_bic_status(self) -> Response:
        """Get the status of the local OpenSanctions BIC mirror."""
        return self._request("GET", "/admin/maintenance/opensanctions-bic-status")

    def get_tranco_status(self) -> Response:
        """Get the status of the local Tranco top-sites mirror."""
        return self._request("GET", "/admin/maintenance/tranco-status")

    def get_data_quality_settings(self) -> Response:
        """Get the data quality settings of the caller's organisation."""
        return self._request("GET", "/admin/maintenance/data-quality-settings")

    def update_data_quality_settings(
        self, auto_propagate_confidence: bool, max_knn_cosine_distance: float
    ) -> Response:
        """Replace the data quality settings of the caller's organisation."""
        return self._request(
            "PUT",
            "/admin/maintenance/data-quality-settings",
            json_data={
                "auto_propagate_confidence": auto_propagate_confidence,
                "max_knn_cosine_distance": max_knn_cosine_distance,
            },
        )

    def start_enrichment_reprocess(
        self,
        types: Optional[List[str]] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include_test: Optional[bool] = None,
        backfill_only: Optional[bool] = None,
        mode: Optional[str] = None,
    ) -> Response:
        """Start the enrichment reprocess job; AFTER and BEFORE are RFC 3339 times."""
        body = _without_none(
            {
                "types": types,
                "after": after,
                "before": before,
                "include_test": include_test,
                "backfill_only": backfill_only,
                "mode": mode,
            }
        )
        return self._request("POST", "/admin/enrichment-reprocess", json_data=body)

    def start_extraction_reprocess(
        self,
        identifier_types: Optional[List[str]] = None,
        service_filter: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include_test: Optional[bool] = None,
    ) -> Response:
        """Start the extraction reprocess job; AFTER and BEFORE are RFC 3339 times."""
        body = _without_none(
            {
                "identifier_types": identifier_types,
                "service_filter": service_filter,
                "after": after,
                "before": before,
                "include_test": include_test,
            }
        )
        return self._request("POST", "/admin/extraction-reprocess", json_data=body)

    def start_nsfw_scan(self, rescan_all: Optional[bool] = None) -> Response:
        """Start the NSFW scan over unscanned media, or over all media with RESCAN_ALL."""
        body = _without_none({"rescan_all": rescan_all})
        return self._request("POST", "/admin/nsfw-scan", json_data=body)

    def get_reprocess_status(self, job: str) -> Response:
        """Get the state of the reprocess job JOB."""
        _require(job, REPROCESS_JOBS, "reprocess job")
        return self._request("GET", f"/admin/{job}")

    def cancel_reprocess(self, job: str) -> Response:
        """Cancel the running reprocess job JOB."""
        _require(job, REPROCESS_JOBS, "reprocess job")
        return self._request("POST", f"/admin/{job}/cancel")

    def get_task_queue_overview(self) -> Response:
        """Get the task count per queue and state, and the worker servers."""
        return self._request("GET", "/admin/task-queue/overview")

    def list_tasks(
        self,
        queue: str,
        state: str,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Response:
        """List one page of the tasks of QUEUE in STATE."""
        _require(state, TASK_STATES, "task state")
        params = _without_none({"page": page, "page_size": page_size})
        return self._request("GET", f"{_queue_path(queue)}/tasks/{state}", params=params or None)

    def get_task(self, queue: str, state: str, task_id: str) -> Response:
        """Get one task with its payload and result."""
        _require(state, TASK_STATES, "task state")
        return self._request("GET", f"{_queue_path(queue)}/tasks/{state}/{quote(task_id, safe='')}")

    def delete_task(self, queue: str, task_id: str) -> Response:
        """Delete one task from QUEUE."""
        return self._request("DELETE", f"{_queue_path(queue)}/tasks/{quote(task_id, safe='')}")

    def cancel_task(self, queue: str, task_id: str) -> Response:
        """Send a cancel signal to one active task."""
        return self._request("POST", f"{_queue_path(queue)}/tasks/{quote(task_id, safe='')}/cancel")

    def retry_task(self, queue: str, task_id: str) -> Response:
        """Run one scheduled, retry or archived task now."""
        return self._request("POST", f"{_queue_path(queue)}/tasks/{quote(task_id, safe='')}/retry")

    def retry_archived_tasks(self, queue: str) -> Response:
        """Run every archived task of QUEUE now."""
        return self._request("POST", f"{_queue_path(queue)}/retry-all-archived")

    def cleanup_abandoned_drafts(self, days: Optional[int] = None) -> Response:
        """Delete journal drafts not updated for DAYS days (server default 90, minimum 30)."""
        params = _without_none({"days": days})
        return self._request("POST", "/admin/drafts/cleanup", params=params or None)

    def refresh_analytics(self) -> Response:
        """Refresh the analytics materialised views."""
        return self._request("POST", "/analytics/refresh")

    def get_redis_info(self) -> Response:
        """Get a snapshot of the Redis server statistics."""
        return self._request("GET", "/admin/redis/info")
