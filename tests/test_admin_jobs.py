"""Unit tests for the background job admin methods."""

from unittest.mock import Mock

import pytest

from scambus_client._admin_jobs import (
    MAINTENANCE_FORCE_JOBS,
    MAINTENANCE_JOBS,
    MAINTENANCE_MISSING_COUNT_JOBS,
    MAINTENANCE_PROGRESS_JOBS,
    MAINTENANCE_RESET_JOBS,
    REPROCESS_JOBS,
)

PROGRESS_JOBS = [
    "rebuild-identifier-tags",
    "rebuild-graph-edges",
    "rebuild-network-sizes",
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-tranco-checks",
]
RESET_JOBS = [name for name in PROGRESS_JOBS if name != "rebuild-network-sizes"]
MISSING_COUNT_JOBS = [
    "backfill-embeddings",
    "backfill-conversation-chunks",
    "backfill-cluster-member-contexts",
    "backfill-media-vision",
    "backfill-identifier-source-media",
    "backfill-media-thumbnails",
    "backfill-media-transcripts",
    "backfill-tranco-checks",
]
START_ONLY_JOBS = ["backfill-scam-confidence-scope"]

API = "https://api.test.scambus.net/api"
QUEUE = f"{API}/admin/task-queue/queues/maintenance"


@pytest.fixture
def api(client):
    response = Mock(status_code=200)
    response.json.return_value = {"status": "ok"}
    client.session.request.return_value = response
    return client


def sent(client):
    kwargs = client.session.request.call_args.kwargs
    return kwargs["method"], kwargs["url"], kwargs["json"], kwargs["params"]


class TestMaintenance:
    def test_job_tuples_match_backend_routes(self):
        assert set(MAINTENANCE_JOBS) == set(PROGRESS_JOBS + MISSING_COUNT_JOBS + START_ONLY_JOBS)
        assert list(MAINTENANCE_PROGRESS_JOBS) == PROGRESS_JOBS
        assert list(MAINTENANCE_RESET_JOBS) == RESET_JOBS
        assert list(MAINTENANCE_FORCE_JOBS) == ["backfill-cluster-member-contexts"]
        assert list(MAINTENANCE_MISSING_COUNT_JOBS) == MISSING_COUNT_JOBS
        assert list(REPROCESS_JOBS) == ["enrichment-reprocess", "extraction-reprocess", "nsfw-scan"]

    @pytest.mark.parametrize(
        "name", sorted(set(PROGRESS_JOBS + MISSING_COUNT_JOBS + START_ONLY_JOBS))
    )
    def test_start_posts_to_job_route(self, api, name):
        assert api.start_maintenance_job(name) == {"status": "ok"}

        assert sent(api) == ("POST", f"{API}/admin/maintenance/{name}", None, None)

    def test_start_with_reset_and_force(self, api):
        api.start_maintenance_job("backfill-cluster-member-contexts", reset=True, force=True)

        assert sent(api) == (
            "POST",
            f"{API}/admin/maintenance/backfill-cluster-member-contexts",
            None,
            {"reset": "true", "force": "true"},
        )

    def test_start_refuses_reset_on_job_without_checkpoint(self, api):
        with pytest.raises(ValueError, match="resettable maintenance job"):
            api.start_maintenance_job("backfill-media-thumbnails", reset=True)
        api.session.request.assert_not_called()

    def test_start_refuses_force_on_other_job(self, api):
        with pytest.raises(ValueError, match="forceable maintenance job"):
            api.start_maintenance_job("backfill-embeddings", force=True)
        api.session.request.assert_not_called()

    @pytest.mark.parametrize("name", RESET_JOBS)
    def test_start_with_reset(self, api, name):
        api.start_maintenance_job(name, reset=True)

        assert sent(api) == ("POST", f"{API}/admin/maintenance/{name}", None, {"reset": "true"})

    @pytest.mark.parametrize("name", PROGRESS_JOBS)
    def test_progress(self, api, name):
        api.get_maintenance_progress(name)

        assert sent(api) == ("GET", f"{API}/admin/maintenance/{name}/progress", None, None)

    @pytest.mark.parametrize(
        "name, path",
        [
            ("backfill-embeddings", "missing-embeddings-count"),
            ("backfill-conversation-chunks", "missing-conversation-chunks-count"),
            ("backfill-cluster-member-contexts", "missing-cluster-member-contexts-count"),
            ("backfill-media-vision", "missing-media-vision-count"),
            ("backfill-identifier-source-media", "missing-identifier-source-media-count"),
            ("backfill-media-thumbnails", "missing-media-thumbnails-count"),
            ("backfill-media-transcripts", "missing-media-transcripts-count"),
            ("backfill-tranco-checks", "missing-tranco-checks-count"),
        ],
    )
    def test_missing_count(self, api, name, path):
        api.get_maintenance_missing_count(name)

        assert sent(api) == ("GET", f"{API}/admin/maintenance/{path}", None, None)

    @pytest.mark.parametrize(
        "call",
        [
            lambda c: c.start_maintenance_job("rebuild-everything"),
            lambda c: c.get_maintenance_progress("backfill-media-thumbnails"),
            lambda c: c.get_maintenance_missing_count("rebuild-graph-edges"),
            lambda c: c.get_reprocess_status("url-consolidation"),
            lambda c: c.cancel_reprocess("enrichment"),
            lambda c: c.list_tasks("default", "dead"),
            lambda c: c.get_task("default", "failed", "abc"),
        ],
    )
    def test_unknown_name_is_refused(self, api, call):
        with pytest.raises(ValueError, match="unknown"):
            call(api)
        api.session.request.assert_not_called()

    def test_scam_tag_cleanup_dry_run(self, api):
        api.start_scam_tag_cleanup(dry_run=True)

        assert sent(api) == (
            "POST",
            f"{API}/admin/maintenance/scam-tag-cleanup",
            None,
            {"dry_run": "true"},
        )

    def test_scam_tag_cleanup_real_run_sends_no_params(self, api):
        api.start_scam_tag_cleanup()

        assert sent(api) == ("POST", f"{API}/admin/maintenance/scam-tag-cleanup", None, None)

    @pytest.mark.parametrize(
        "method, verb, path",
        [
            ("get_scam_tag_cleanup", "GET", "/admin/maintenance/scam-tag-cleanup"),
            ("reset_failed_media_vision", "POST", "/admin/maintenance/reset-failed-media-vision"),
            ("get_embedding_usage", "GET", "/admin/maintenance/embedding-usage"),
            ("get_opensanctions_bic_status", "GET", "/admin/maintenance/opensanctions-bic-status"),
            ("get_tranco_status", "GET", "/admin/maintenance/tranco-status"),
            ("get_data_quality_settings", "GET", "/admin/maintenance/data-quality-settings"),
            ("get_task_queue_overview", "GET", "/admin/task-queue/overview"),
            ("refresh_analytics", "POST", "/analytics/refresh"),
            ("get_redis_info", "GET", "/admin/redis/info"),
        ],
    )
    def test_no_argument_calls(self, api, method, verb, path):
        getattr(api, method)()

        assert sent(api) == (verb, f"{API}{path}", None, None)

    def test_update_data_quality_settings(self, api):
        api.update_data_quality_settings(True, 0.35)

        assert sent(api) == (
            "PUT",
            f"{API}/admin/maintenance/data-quality-settings",
            {"auto_propagate_confidence": True, "max_knn_cosine_distance": 0.35},
            None,
        )


class TestReprocess:
    def test_enrichment_start_sends_given_fields(self, api):
        api.start_enrichment_reprocess(
            types=["phone"],
            after="2026-01-01T00:00:00Z",
            backfill_only=True,
            mode="checks",
        )

        assert sent(api) == (
            "POST",
            f"{API}/admin/enrichment-reprocess",
            {
                "types": ["phone"],
                "after": "2026-01-01T00:00:00Z",
                "backfill_only": True,
                "mode": "checks",
            },
            None,
        )

    def test_extraction_start_uses_identifier_types(self, api):
        api.start_extraction_reprocess(
            identifier_types=["email"],
            service_filter="whatsapp",
            before="2026-02-01T00:00:00Z",
            include_test=True,
        )

        assert sent(api) == (
            "POST",
            f"{API}/admin/extraction-reprocess",
            {
                "identifier_types": ["email"],
                "service_filter": "whatsapp",
                "before": "2026-02-01T00:00:00Z",
                "include_test": True,
            },
            None,
        )

    def test_start_without_options_sends_empty_body(self, api):
        api.start_nsfw_scan()

        assert sent(api) == ("POST", f"{API}/admin/nsfw-scan", {}, None)

    def test_nsfw_rescan_all(self, api):
        api.start_nsfw_scan(rescan_all=True)

        assert sent(api) == ("POST", f"{API}/admin/nsfw-scan", {"rescan_all": True}, None)

    @pytest.mark.parametrize("job", ["enrichment-reprocess", "extraction-reprocess", "nsfw-scan"])
    def test_status_and_cancel(self, api, job):
        api.get_reprocess_status(job)
        assert sent(api) == ("GET", f"{API}/admin/{job}", None, None)

        api.cancel_reprocess(job)
        assert sent(api) == ("POST", f"{API}/admin/{job}/cancel", None, None)


class TestTaskQueue:
    def test_list_tasks_with_paging(self, api):
        api.list_tasks("maintenance", "archived", page=2, page_size=50)

        assert sent(api) == (
            "GET",
            f"{QUEUE}/tasks/archived",
            None,
            {"page": 2, "page_size": 50},
        )

    def test_list_tasks_without_paging(self, api):
        api.list_tasks("maintenance", "pending")

        assert sent(api) == ("GET", f"{QUEUE}/tasks/pending", None, None)

    def test_get_task_escapes_id(self, api):
        api.get_task("maintenance", "retry", "scam:tag/1")

        assert sent(api) == ("GET", f"{QUEUE}/tasks/retry/scam%3Atag%2F1", None, None)

    @pytest.mark.parametrize(
        "method, verb, suffix",
        [
            ("delete_task", "DELETE", ""),
            ("cancel_task", "POST", "/cancel"),
            ("retry_task", "POST", "/retry"),
        ],
    )
    def test_task_actions(self, api, method, verb, suffix):
        getattr(api, method)("maintenance", "task-1")

        assert sent(api) == (verb, f"{QUEUE}/tasks/task-1{suffix}", None, None)

    def test_retry_archived(self, api):
        api.retry_archived_tasks("maintenance")

        assert sent(api) == ("POST", f"{QUEUE}/retry-all-archived", None, None)


class TestDrafts:
    def test_cleanup_with_days(self, api):
        api.cleanup_abandoned_drafts(days=45)

        assert sent(api) == ("POST", f"{API}/admin/drafts/cleanup", None, {"days": 45})

    def test_cleanup_uses_server_default(self, api):
        api.cleanup_abandoned_drafts()

        assert sent(api) == ("POST", f"{API}/admin/drafts/cleanup", None, None)
