import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.celery_app import celery_app
from app.db.models import PullRequest, Repository, Workspace
from app.db.session import AsyncSessionLocal
from app.llm import get_default_llm_provider
from app.schemas.handoffs import (
    ExtractionRequest,
    ReanalysisRequest,
    RetentionCleanupTaskResult,
    WebhookTaskPayload,
)
from app.services.digest_generator import generate_weekly_digest
from app.services.extractor import extract_from_pr
from app.services.learning_saver import save_learning_items
from app.services.loki import publish_retention_cleanup_result
from app.services.retention import cleanup_expired_pr_source_data
from app.services.pr_processor import process_pr_event
from app.services.weekly_digests import resolve_previous_week_period

logger = logging.getLogger(__name__)


def _payload_context(payload: dict | WebhookTaskPayload) -> dict[str, object]:
    data = payload.model_dump(mode="python") if isinstance(payload, WebhookTaskPayload) else payload
    repo_data = data.get("repository", {})
    pr_data = data.get("pull_request", {})
    action = data.get("action", "")
    repo = repo_data.get("full_name", "")
    pr_number = pr_data.get("number")
    installation_id = data.get("installation", {}).get("id")
    correlation_id = data.get("correlation_id") or _build_correlation_id(
        data.get("event_type", ""),
        action,
        repo,
        pr_number,
        installation_id,
    )
    return {
        "action": action,
        "repo": repo,
        "pr_number": pr_number,
        "installation_id": installation_id,
        "correlation_id": correlation_id,
    }


def _build_correlation_id(
    event_type: str,
    action: str,
    repo: str,
    pr_number: object,
    installation_id: object,
) -> str:
    pr_part = "na" if pr_number is None else str(pr_number)
    installation_part = "na" if installation_id is None else str(installation_id)
    return f"github-webhook:{event_type or 'unknown'}:{action or 'unknown'}:{repo or 'unknown'}:{pr_part}:{installation_part}"


def _schedule_context(result: dict) -> dict[str, object]:
    return {
        "year": result.get("year"),
        "week": result.get("week"),
        "workspace_count": result.get("workspace_count"),
        "generated_count": result.get("generated_count"),
    }


def _reanalysis_pr_context(pr_id: int, workspace_id: int, user_id: int) -> dict[str, int]:
    return {
        "pr_id": pr_id,
        "workspace_id": workspace_id,
        "user_id": user_id,
    }


def _learning_extraction_context(request: ExtractionRequest | ReanalysisRequest | dict[str, Any]) -> dict[str, Any]:
    data = request.model_dump(mode="python") if isinstance(request, (ExtractionRequest, ReanalysisRequest)) else request
    return {
        "workspace_id": data.get("workspace_id"),
        "pr_id": data.get("pr_id"),
        "repo": data.get("repo"),
        "pr_number": data.get("pr_number"),
        "installation_id": data.get("installation_id"),
        "correlation_id": data.get("correlation_id"),
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_pr_task(self, payload: dict) -> dict:
    """
    Process a webhook payload and extract PR learnings in the background.
    Returns: {"status": "ok", "pr_number": int} or raises
    """
    payload_model = WebhookTaskPayload.model_validate(payload)
    context = _payload_context(payload_model)
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "extract_pr_task started attempt=%d action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
        retries + 1,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
    )
    try:
        result = asyncio.run(_run_extract_pr(payload_model))
        logger.info(
            "extract_pr_task completed attempt=%d action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s status=%s",
            retries + 1,
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "extract_pr_task failed attempt=%d/%d final=%s action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            retries + 1,
            self.max_retries,
            is_final,
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
            exc_info=True,
        )
        raise self.retry(exc=exc)


async def _run_extract_pr(payload: dict | WebhookTaskPayload) -> dict:
    payload_model = WebhookTaskPayload.model_validate(payload)
    context = _payload_context(payload_model)
    logger.info(
        "extract_pr_pipeline stage=handoff action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
    )

    async with AsyncSessionLocal() as db:
        logger.info(
            "extract_pr_pipeline stage=ingest action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
        )
        extraction_request = await process_pr_event(
            payload_model.model_dump(mode="python", exclude_unset=True),
            db,
        )

    if extraction_request is None:
        return {"status": "skipped", "pr_number": payload_model.pull_request.get("number", 0)}

    extraction_request = ExtractionRequest.model_validate(extraction_request)

    logger.info(
        "extract_pr_pipeline stage=extract_handoff action=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
    )
    extract_learning_items_task.delay(extraction_request.model_dump(mode="python", exclude_unset=True))

    pr_number = payload_model.pull_request.get("number", 0)
    return {"status": "queued", "pr_number": pr_number}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_learning_items_task(self, extraction_request: dict) -> dict:
    request_model = ExtractionRequest.model_validate(extraction_request)
    context = _learning_extraction_context(request_model)
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "extract_learning_items_task started attempt=%d workspace_id=%s pr_id=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
        retries + 1,
        context["workspace_id"],
        context["pr_id"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
    )
    try:
        result = asyncio.run(_run_extract_learning_items(request_model))
        logger.info(
            "extract_learning_items_task completed attempt=%d workspace_id=%s pr_id=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s status=%s",
            retries + 1,
            context["workspace_id"],
            context["pr_id"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "extract_learning_items_task failed attempt=%d/%d final=%s workspace_id=%s pr_id=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            retries + 1,
            self.max_retries,
            is_final,
            context["workspace_id"],
            context["pr_id"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
            exc_info=True,
        )
        raise self.retry(exc=exc)


async def _run_extract_learning_items(extraction_request: ExtractionRequest | dict[str, Any]) -> dict:
    request_model = ExtractionRequest.model_validate(extraction_request)
    context = _learning_extraction_context(request_model)
    logger.info(
        "extract_learning_items_pipeline stage=provider_call workspace_id=%s pr_id=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
        context["workspace_id"],
        context["pr_id"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
        context["correlation_id"],
    )
    provider = get_default_llm_provider()
    result = await extract_from_pr(request_model.pr_dict, provider)

    async with AsyncSessionLocal() as db:
        logger.info(
            "extract_learning_items_pipeline stage=save workspace_id=%s pr_id=%s repo=%s pr_number=%s installation_id=%s correlation_id=%s",
            context["workspace_id"],
            context["pr_id"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            context["correlation_id"],
        )
        saved = await save_learning_items(
            result,
            request_model.pr_id,
            db,
            created_by_user_id=request_model.created_by_user_id,
        )
    return {"status": "ok", "pr_id": request_model.pr_id, "learning_count": len(saved)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def reanalyze_pr_task(
    self,
    pr_id: int | dict[str, Any],
    workspace_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Persisted reanalysis path for an existing PR."""
    if isinstance(pr_id, dict):
        request_data = pr_id
        pr_id = int(request_data["pr_id"])
        workspace_id = int(request_data["workspace_id"])
        user_id = int(request_data["user_id"])
    else:
        pr_id = int(pr_id)
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "reanalyze_pr_task started attempt=%d pr_id=%d workspace_id=%d user_id=%d",
        retries + 1,
        pr_id,
        workspace_id,
        user_id,
    )
    try:
        result = asyncio.run(_run_reanalysis(pr_id, workspace_id or 0, user_id or 0))
        logger.info(
            "reanalyze_pr_task completed attempt=%d pr_id=%d workspace_id=%d user_id=%d status=%s",
            retries + 1,
            pr_id,
            workspace_id,
            user_id,
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "reanalyze_pr_task failed attempt=%d/%d final=%s pr_id=%d workspace_id=%d user_id=%d",
            retries + 1,
            self.max_retries,
            is_final,
            pr_id,
            workspace_id,
            user_id,
            exc_info=True,
        )
        raise self.retry(exc=exc)


async def _run_reanalysis(pr_id: int, workspace_id: int, user_id: int) -> dict:
    context = _reanalysis_pr_context(pr_id, workspace_id, user_id)

    async with AsyncSessionLocal() as db:
        logger.info(
            "reanalyze_pr_pipeline stage=lookup pr_id=%d workspace_id=%d user_id=%d",
            context["pr_id"],
            context["workspace_id"],
            context["user_id"],
        )
        pr = await _load_reanalysis_pull_request(db, pr_id, workspace_id)
        if not pr:
            return {"status": "not_found", "pr_id": pr_id}

        logger.info(
            "reanalyze_pr_pipeline stage=assemble pr_id=%d workspace_id=%d user_id=%d",
            context["pr_id"],
            context["workspace_id"],
            context["user_id"],
        )
        pr_dict = _build_reanalysis_pr_dict(pr_id, pr)
        logger.info(
            "reanalyze_pr_pipeline stage=extract_handoff pr_id=%d workspace_id=%d user_id=%d",
            context["pr_id"],
            context["workspace_id"],
            context["user_id"],
        )
        extract_learning_items_task.delay(
            ExtractionRequest(
                workspace_id=workspace_id,
                pr_id=pr_id,
                created_by_user_id=user_id,
                repo=pr.repository.full_name,
                pr_number=pr.github_pr_number,
                installation_id=None,
                correlation_id=f"reanalysis:{workspace_id}:{pr_id}:{user_id}",
                pr_dict=pr_dict,
            ).model_dump(mode="python", exclude_unset=True)
        )

    return {"status": "queued", "pr_id": pr_id}


async def _load_reanalysis_pull_request(db, pr_id: int, workspace_id: int):
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(selectinload(PullRequest.review_comments), selectinload(PullRequest.repository))
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


def _build_reanalysis_pr_dict(pr_id: int, pr: PullRequest) -> dict[str, Any]:
    return {
        "pr_id": f"db-{pr_id}",
        "title": pr.title,
        "description": pr.body or "",
        "diff_summary": "",
        "review_comments": [
            {
                "id": str(comment.github_comment_id),
                "author": comment.author,
                "body": comment.body,
                "file": comment.file_path or "",
                "line": comment.line_number,
                "diff_hunk": comment.diff_hunk or "",
                "resolved": comment.resolved,
            }
            for comment in pr.review_comments
        ],
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_digest_task(
    self,
    year: int,
    week: int,
    workspace_id: int,
) -> dict:
    """
    Generate a weekly digest for the given workspace in the background.
    Returns: {"status": "ok", "digest_id": int}
    """
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "generate_digest_task started attempt=%d year=%d week=%d workspace_id=%d",
        retries + 1,
        year,
        week,
        workspace_id,
    )
    try:
        result = asyncio.run(_run_generate_digest(year, week, workspace_id))
        logger.info(
            "generate_digest_task completed attempt=%d year=%d week=%d workspace_id=%d status=%s",
            retries + 1,
            year,
            week,
            workspace_id,
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "generate_digest_task failed attempt=%d/%d final=%s year=%d week=%d workspace_id=%d",
            retries + 1,
            self.max_retries,
            is_final,
            year,
            week,
            workspace_id,
            exc_info=True,
        )
        raise self.retry(exc=exc)


async def _run_generate_digest(
    year: int,
    week: int,
    workspace_id: int,
) -> dict:
    provider = get_default_llm_provider()

    async with AsyncSessionLocal() as db:
        digest = await generate_weekly_digest(
            year,
            week,
            workspace_id,
            provider,
            db,
        )
    return {"status": "ok", "digest_id": digest.id}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=600)
def generate_scheduled_weekly_digests_task(self) -> dict:
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "generate_scheduled_weekly_digests_task started attempt=%d",
        retries + 1,
    )
    try:
        result = asyncio.run(_run_generate_scheduled_weekly_digests())
        context = _schedule_context(result)
        logger.info(
            "generate_scheduled_weekly_digests_task completed attempt=%d year=%s week=%s workspace_count=%s generated_count=%s status=%s",
            retries + 1,
            context["year"],
            context["week"],
            context["workspace_count"],
            context["generated_count"],
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "generate_scheduled_weekly_digests_task failed attempt=%d/%d final=%s",
            retries + 1,
            self.max_retries,
            is_final,
            exc_info=True,
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1, default_retry_delay=3600)
def cleanup_retention_task(self) -> dict:
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info("cleanup_retention_task started attempt=%d", retries + 1)
    try:
        result = asyncio.run(_run_cleanup_retention())
        logger.info(
            "cleanup_retention_task completed attempt=%d deleted_pull_requests=%s deleted_review_comments=%s detached_learning_items=%s deleted_expired_learning_items=%s deleted_weekly_digests=%s pr_source_cutoff=%s log_metadata_cutoff=%s learning_cutoff=%s digest_cutoff=%s status=%s",
            retries + 1,
            result.get("deleted_pull_requests"),
            result.get("deleted_review_comments"),
            result.get("detached_learning_items"),
            result.get("deleted_expired_learning_items"),
            result.get("deleted_weekly_digests"),
            result.get("pr_source_cutoff"),
            result.get("log_metadata_cutoff"),
            result.get("learning_cutoff"),
            result.get("digest_cutoff"),
            result.get("status"),
        )
        return result
    except Exception as exc:
        is_final = retries + 1 >= self.max_retries
        log = logger.error if is_final else logger.warning
        log(
            "cleanup_retention_task failed attempt=%d/%d final=%s",
            retries + 1,
            self.max_retries,
            is_final,
            exc_info=True,
        )
        raise self.retry(exc=exc)


async def _run_generate_scheduled_weekly_digests() -> dict:
    period = resolve_previous_week_period()
    provider = get_default_llm_provider()

    async with AsyncSessionLocal() as db:
        workspace_ids = list((await db.scalars(select(Workspace.id))).all())
        generated_count = 0
        for workspace_id in workspace_ids:
            await generate_weekly_digest(
                period.year,
                period.week,
                workspace_id,
                provider,
                db,
            )
            generated_count += 1

    return {
        "status": "ok",
        "year": period.year,
        "week": period.week,
        "workspace_count": len(workspace_ids),
        "generated_count": generated_count,
    }


async def _run_cleanup_retention() -> dict:
    async with AsyncSessionLocal() as db:
        cleanup = await cleanup_expired_pr_source_data(db)
    result = RetentionCleanupTaskResult(
        status="ok",
        deleted_pull_requests=cleanup.deleted_pull_requests,
        deleted_review_comments=cleanup.deleted_review_comments,
        detached_learning_items=cleanup.detached_learning_items,
        deleted_expired_learning_items=cleanup.deleted_expired_learning_items,
        deleted_weekly_digests=cleanup.deleted_weekly_digests,
        pr_source_cutoff=cleanup.window.pr_source_cutoff,
        log_metadata_cutoff=cleanup.window.log_metadata_cutoff,
        learning_cutoff=cleanup.window.learning_cutoff,
        digest_cutoff=cleanup.window.digest_cutoff,
    )
    try:
        loki_published = await publish_retention_cleanup_result(result, as_of=cleanup.window.as_of)
    except Exception:
        logger.warning("Failed to publish retention cleanup audit log to Loki", exc_info=True)
        loki_published = False
    payload = result.model_dump(mode="json")
    payload["loki_published"] = loki_published
    return payload
