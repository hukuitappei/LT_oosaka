import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _payload_context(payload: dict) -> dict[str, object]:
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})
    return {
        "action": payload.get("action", ""),
        "repo": repo_data.get("full_name", ""),
        "pr_number": pr_data.get("number"),
        "installation_id": payload.get("installation", {}).get("id"),
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_pr_task(self, payload: dict) -> dict:
    """
    Process a webhook payload and extract PR learnings in the background.
    Returns: {"status": "ok", "pr_number": int} or raises
    """
    context = _payload_context(payload)
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "extract_pr_task started attempt=%d action=%s repo=%s pr_number=%s installation_id=%s",
        retries + 1,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
    try:
        result = asyncio.run(_run_extract_pr(payload))
        logger.info(
            "extract_pr_task completed attempt=%d action=%s repo=%s pr_number=%s installation_id=%s status=%s",
            retries + 1,
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
            result.get("status"),
        )
        return result
    except Exception as exc:
        logger.exception(
            "extract_pr_task failed attempt=%d action=%s repo=%s pr_number=%s installation_id=%s, retrying...",
            retries + 1,
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
        )
        raise self.retry(exc=exc)


async def _run_extract_pr(payload: dict) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.services.pr_processor import process_pr_event

    async with AsyncSessionLocal() as db:
        await process_pr_event(payload, db)

    pr_number = payload.get("pull_request", {}).get("number", 0)
    return {"status": "ok", "pr_number": pr_number}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def reanalyze_pr_task(self, pr_id: int, workspace_id: int, user_id: int) -> dict:
    """Persisted reanalysis path for an existing PR."""
    retries = getattr(getattr(self, "request", None), "retries", 0)
    logger.info(
        "reanalyze_pr_task started attempt=%d pr_id=%d workspace_id=%d user_id=%d",
        retries + 1,
        pr_id,
        workspace_id,
        user_id,
    )
    try:
        result = asyncio.run(_run_reanalysis(pr_id, workspace_id, user_id))
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
        logger.exception(
            "reanalyze_pr_task failed attempt=%d pr_id=%d workspace_id=%d user_id=%d, retrying...",
            retries + 1,
            pr_id,
            workspace_id,
            user_id,
        )
        raise self.retry(exc=exc)


async def _run_reanalysis(pr_id: int, workspace_id: int, user_id: int) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.models import PullRequest, Repository
    from app.db.session import AsyncSessionLocal
    from app.llm import get_default_llm_provider
    from app.services.extractor import extract_from_pr
    from app.services.learning_saver import save_learning_items

    async with AsyncSessionLocal() as db:
        pr = await db.scalar(
            select(PullRequest)
            .join(Repository, PullRequest.repository_id == Repository.id)
            .options(selectinload(PullRequest.review_comments))
            .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
        )
        if not pr:
            return {"status": "not_found", "pr_id": pr_id}

        pr_dict = {
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

        provider = get_default_llm_provider()
        result = await extract_from_pr(pr_dict, provider)
        await save_learning_items(result, pr_id, db, created_by_user_id=user_id)

    return {"status": "ok", "pr_id": pr_id}


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
        logger.exception(
            "generate_digest_task failed attempt=%d year=%d week=%d workspace_id=%d, retrying...",
            retries + 1,
            year,
            week,
            workspace_id,
        )
        raise self.retry(exc=exc)


async def _run_generate_digest(
    year: int,
    week: int,
    workspace_id: int,
) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.llm import get_default_llm_provider
    from app.services.digest_generator import generate_weekly_digest

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
