from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.db.models import PullRequest, LearningItem, User
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/pull-requests", tags=["pull-requests"])


class LearningItemOut(BaseModel):
    id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PullRequestDetail(BaseModel):
    id: int
    github_pr_number: int
    title: str
    state: str
    author: str
    github_url: str
    processed: bool
    created_at: datetime
    learning_items: list[LearningItemOut] = []

    model_config = {"from_attributes": True}


@router.get("/{pr_id}", response_model=PullRequestDetail)
async def get_pull_request(
    pr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    pr = await db.scalar(
        select(PullRequest)
        .options(selectinload(PullRequest.learning_items))
        .where(PullRequest.id == pr_id)
    )
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.post("/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    pr_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """保存済みPRを再分析して learning_items を再生成する"""
    pr = await db.get(PullRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")

    background_tasks.add_task(_run_reanalysis, pr_id)
    return {"status": "accepted", "pr_id": pr_id}


async def _run_reanalysis(pr_id: int) -> None:
    from app.db.session import AsyncSessionLocal
    from app.db.models import PullRequest
    from app.services.extractor import extract_from_pr
    from app.services.learning_saver import save_learning_items

    async with AsyncSessionLocal() as db:
        pr = await db.get(PullRequest, pr_id)
        if not pr:
            return

        # fixture ベースで再抽出（GitHub連携なし）
        pr_dict = {
            "pr_id": f"db-{pr_id}",
            "title": pr.title,
            "description": pr.body or "",
            "diff_summary": "",
            "review_comments": [],
        }

        if settings.anthropic_api_key:
            from app.llm.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        else:
            from app.llm.ollama_provider import OllamaProvider
            provider = OllamaProvider(host=settings.ollama_base_url)

        result = await extract_from_pr(pr_dict, provider)
        await save_learning_items(result, pr_id, db)
