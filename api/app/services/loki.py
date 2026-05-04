from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.schemas.handoffs import RetentionCleanupTaskResult

logger = logging.getLogger(__name__)


def loki_is_configured() -> bool:
    return bool(settings.loki_push_url)


def _build_loki_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.loki_tenant_id:
        headers["X-Scope-OrgID"] = settings.loki_tenant_id
    return headers


def _build_loki_auth() -> tuple[str, str] | None:
    if settings.loki_username:
        return (settings.loki_username, settings.loki_password)
    return None


def _build_retention_stream_labels() -> dict[str, str]:
    return {
        "app": "lt_oosaka",
        "env": settings.app_env,
        "job": settings.loki_retention_job,
        "event": "retention_cleanup",
    }


def _build_retention_log_line(result: RetentionCleanupTaskResult) -> str:
    payload = {
        "status": result.status,
        "deleted_pull_requests": result.deleted_pull_requests,
        "deleted_review_comments": result.deleted_review_comments,
        "detached_learning_items": result.detached_learning_items,
        "deleted_expired_learning_items": result.deleted_expired_learning_items,
        "deleted_weekly_digests": result.deleted_weekly_digests,
        "pr_source_cutoff": result.pr_source_cutoff.isoformat(),
        "log_metadata_cutoff": result.log_metadata_cutoff.isoformat(),
        "learning_cutoff": result.learning_cutoff.isoformat(),
        "digest_cutoff": result.digest_cutoff.isoformat(),
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


async def publish_retention_cleanup_result(
    result: RetentionCleanupTaskResult,
    *,
    as_of: datetime | None = None,
) -> bool:
    if not loki_is_configured():
        return False

    timestamp = as_of or datetime.now(timezone.utc)
    timestamp_ns = str(int(timestamp.timestamp() * 1_000_000_000))
    body = {
        "streams": [
            {
                "stream": _build_retention_stream_labels(),
                "values": [[timestamp_ns, _build_retention_log_line(result)]],
            }
        ]
    }

    async with httpx.AsyncClient(timeout=settings.loki_timeout_seconds) as client:
        response = await client.post(
            settings.loki_push_url,
            headers=_build_loki_headers(),
            auth=_build_loki_auth(),
            json=body,
        )
        response.raise_for_status()

    logger.info(
        "Published retention cleanup audit log to Loki job=%s status=%s",
        settings.loki_retention_job,
        result.status,
    )
    return True
