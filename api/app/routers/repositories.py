from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
from app.db.session import get_db
from app.db.models import Repository, PullRequest

router = APIRouter(prefix="/repositories", tags=["repositories"])


class RepositoryResponse(BaseModel):
    id: int
    github_id: int
    full_name: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PullRequestResponse(BaseModel):
    id: int
    github_pr_number: int
    title: str
    state: str
    author: str
    github_url: str
    processed: bool
    merged_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Repository).order_by(Repository.created_at.desc()))
    return result.scalars().all()


@router.get("/{repo_id}/pull-requests", response_model=list[PullRequestResponse])
async def list_pull_requests(repo_id: int, db: AsyncSession = Depends(get_db)):
    repo = await db.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    result = await db.execute(
        select(PullRequest)
        .where(PullRequest.repository_id == repo_id)
        .order_by(PullRequest.created_at.desc())
    )
    return result.scalars().all()
