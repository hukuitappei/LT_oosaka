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


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def generate_digest_task(
    self,
    year: int,
    week: int,
    workspace_id: int,
    user_id: int | None = None,
) -> dict:
    """
    指定週の週報を非同期で生成する Celery タスク。
    Returns: {"status": "ok", "digest_id": int}
    """
    try:
        return asyncio.run(_run_generate_digest(year, week, workspace_id, user_id))
    except Exception as exc:
        logger.exception("generate_digest_task failed for %d-W%02d", year, week)
        raise self.retry(exc=exc)


async def _run_generate_digest(
    year: int,
    week: int,
    workspace_id: int,
    user_id: int | None,
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
            user_id=user_id,
        )
    return {"status": "ok", "digest_id": digest.id}
