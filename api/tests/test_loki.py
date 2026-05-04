from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_publish_retention_cleanup_result_is_noop_without_url(monkeypatch):
    from app.config import settings
    from app.schemas.handoffs import RetentionCleanupTaskResult
    from app.services.loki import publish_retention_cleanup_result

    monkeypatch.setattr(settings, "loki_push_url", "", raising=False)

    result = await publish_retention_cleanup_result(
        RetentionCleanupTaskResult(
            status="ok",
            deleted_pull_requests=1,
            deleted_review_comments=2,
            detached_learning_items=3,
            deleted_expired_learning_items=4,
            deleted_weekly_digests=5,
            pr_source_cutoff=datetime(2026, 1, 1, tzinfo=timezone.utc),
            log_metadata_cutoff=datetime(2026, 3, 1, tzinfo=timezone.utc),
            learning_cutoff=datetime(2025, 4, 7, tzinfo=timezone.utc),
            digest_cutoff=datetime(2025, 4, 7, tzinfo=timezone.utc),
        )
    )

    assert result is False


@pytest.mark.asyncio
async def test_publish_retention_cleanup_result_posts_to_loki(monkeypatch):
    from app.config import settings
    from app.schemas.handoffs import RetentionCleanupTaskResult
    from app.services import loki

    monkeypatch.setattr(settings, "loki_push_url", "http://loki.local/loki/api/v1/push", raising=False)
    monkeypatch.setattr(settings, "loki_username", "user", raising=False)
    monkeypatch.setattr(settings, "loki_password", "pass", raising=False)
    monkeypatch.setattr(settings, "loki_tenant_id", "tenant-a", raising=False)
    monkeypatch.setattr(settings, "loki_retention_job", "retention-job", raising=False)
    monkeypatch.setattr(settings, "app_env", "test", raising=False)

    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, headers, auth, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["auth"] = auth
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(loki.httpx, "AsyncClient", FakeClient)

    published = await loki.publish_retention_cleanup_result(
        RetentionCleanupTaskResult(
            status="ok",
            deleted_pull_requests=1,
            deleted_review_comments=2,
            detached_learning_items=3,
            deleted_expired_learning_items=4,
            deleted_weekly_digests=5,
            pr_source_cutoff=datetime(2026, 1, 1, tzinfo=timezone.utc),
            log_metadata_cutoff=datetime(2026, 3, 1, tzinfo=timezone.utc),
            learning_cutoff=datetime(2025, 4, 7, tzinfo=timezone.utc),
            digest_cutoff=datetime(2025, 4, 7, tzinfo=timezone.utc),
        ),
        as_of=datetime(2026, 4, 7, 9, 0, 0, tzinfo=timezone.utc),
    )

    assert published is True
    assert captured["url"] == "http://loki.local/loki/api/v1/push"
    assert captured["headers"]["X-Scope-OrgID"] == "tenant-a"
    assert captured["auth"] == ("user", "pass")
    stream = captured["json"]["streams"][0]
    assert stream["stream"] == {
        "app": "lt_oosaka",
        "env": "test",
        "job": "retention-job",
        "event": "retention_cleanup",
    }
    assert stream["values"][0][0] == "1775552400000000000"
    assert "\"detached_learning_items\":3" in stream["values"][0][1]
