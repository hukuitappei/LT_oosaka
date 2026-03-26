from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import LearningItem, PullRequest, Repository, User, Workspace
from app.db.session import AsyncSessionLocal, get_db
from app.dependencies import get_current_user, get_current_workspace, require_workspace_role

router = APIRouter(prefix="/pull-requests", tags=["pull-requests"])


class LearningItemOut(BaseModel):
    id: int
    title: str
    detail: str
    category: str
    confidence: float
    action_for_next_time: str
    evidence: str
    visibility: str
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


async def _get_workspace_pr(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(selectinload(PullRequest.learning_items))
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


@router.get("/{pr_id}", response_model=PullRequestDetail)
async def get_pull_request(
    pr_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    pr = await _get_workspace_pr(db, pr_id, current_workspace.id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.post("/{pr_id}/reanalyze")
async def reanalyze_pull_request(
    pr_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_workspace: Workspace = Depends(get_current_workspace),
):
    await require_workspace_role(
        {"owner", "admin", "member"},
        current_user=current_user,
        current_workspace=current_workspace,
        db=db,
    )
    pr = await _get_workspace_pr(db, pr_id, current_workspace.id)
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")

    background_tasks.add_task(_run_reanalysis, pr_id, current_workspace.id, current_user.id)
    return {"status": "accepted", "pr_id": pr_id}


async def _run_reanalysis(pr_id: int, workspace_id: int, user_id: int) -> None:
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
            return

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
