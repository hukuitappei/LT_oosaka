from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Repository, PullRequest, ReviewComment


async def process_pr_event(payload: dict[str, Any], db: AsyncSession) -> None:
    """Webhook イベントから PR データを DB に保存する"""
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})

    # Repository の upsert
    repo = await db.scalar(
        select(Repository).where(Repository.github_id == repo_data["id"])
    )
    if not repo:
        repo = Repository(
            github_id=repo_data["id"],
            full_name=repo_data["full_name"],
            name=repo_data["name"],
        )
        db.add(repo)
        await db.flush()

    # PullRequest の upsert
    pr = await db.scalar(
        select(PullRequest).where(
            PullRequest.repository_id == repo.id,
            PullRequest.github_pr_number == pr_data["number"],
        )
    )
    if not pr:
        pr = PullRequest(
            repository_id=repo.id,
            github_pr_number=pr_data["number"],
            title=pr_data["title"],
            body=pr_data.get("body", ""),
            state=pr_data["state"],
            author=pr_data["user"]["login"],
            github_url=pr_data["html_url"],
        )
        db.add(pr)

    await db.commit()
