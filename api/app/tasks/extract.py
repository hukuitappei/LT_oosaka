import asyncio
import logging

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_pr_task(self, payload: dict) -> dict:
    """
    Webhook payload を受け取り、非同期で PR 学習抽出を実行する Celery タスク。
    Returns: {"status": "ok", "pr_number": int} or raises
    """
    try:
        return asyncio.run(_run_extract_pr(payload))
    except Exception as exc:
        logger.exception("extract_pr_task failed for payload, retrying...")
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
    try:
        return asyncio.run(_run_reanalysis(pr_id, workspace_id, user_id))
    except Exception as exc:
        logger.exception("reanalyze_pr_task failed for PR %d", pr_id)
        raise self.retry(exc=exc)


async def _run_reanalysis(pr_id: int, workspace_id: int, user_id: int) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.config import settings
    from app.db.models import PullRequest, Repository
    from app.db.session import AsyncSessionLocal
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

        if settings.anthropic_api_key:
            from app.llm.anthropic_provider import AnthropicProvider

            provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        else:
            from app.llm.ollama_provider import OllamaProvider

            provider = OllamaProvider(host=settings.ollama_base_url)

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
    指定週の週報を非同期で生成する Celery タスク。
    Returns: {"status": "ok", "digest_id": int}
    """
    try:
        return asyncio.run(_run_generate_digest(year, week, workspace_id))
    except Exception as exc:
        logger.exception("generate_digest_task failed for %d-W%02d", year, week)
        raise self.retry(exc=exc)


async def _run_generate_digest(
    year: int,
    week: int,
    workspace_id: int,
) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.config import settings
    from app.services.digest_generator import generate_weekly_digest

    if settings.anthropic_api_key:
        from app.llm.anthropic_provider import AnthropicProvider
        provider = AnthropicProvider(api_key=settings.anthropic_api_key)
    elif settings.ollama_base_url:
        from app.llm.ollama_provider import OllamaProvider
        provider = OllamaProvider(host=settings.ollama_base_url)
    else:
        raise ValueError("No LLM provider configured")

    async with AsyncSessionLocal() as db:
        digest = await generate_weekly_digest(
            year,
            week,
            workspace_id,
            provider,
            db,
        )
    return {"status": "ok", "digest_id": digest.id}
