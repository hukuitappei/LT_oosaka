from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import GitHubConnection, PullRequest, Repository, Workspace, WorkspaceMember
from app.schemas.handoffs import ExtractionRequest

logger = logging.getLogger(__name__)


def _parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_pr_dict_from_payload(
    pr_data: dict[str, Any],
    repo_data: dict[str, Any],
    review_comments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "pr_id": f"github-{repo_data['full_name']}-{pr_data['number']}",
        "title": pr_data["title"],
        "description": pr_data.get("body") or "",
        "diff_summary": f"{pr_data.get('changed_files', 0)} files changed, "
        f"+{pr_data.get('additions', 0)} / -{pr_data.get('deletions', 0)}",
        "review_comments": [
            {
                "id": str(c["id"]),
                "author": c["user"]["login"],
                "body": c["body"],
                "file": c.get("path", ""),
                "line": c.get("line") or c.get("original_line"),
                "diff_hunk": c.get("diff_hunk", ""),
                "resolved": False,
            }
            for c in review_comments
            if c.get("body")
        ],
    }


def _webhook_context(payload: dict[str, Any]) -> dict[str, Any]:
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})
    return {
        "action": payload.get("action", ""),
        "repo": repo_data.get("full_name", ""),
        "pr_number": pr_data.get("number"),
        "installation_id": payload.get("installation", {}).get("id"),
        "correlation_id": payload.get("correlation_id"),
    }


async def _resolve_workspace_for_connection(
    db: AsyncSession,
    connection: GitHubConnection | None,
) -> Workspace | None:
    if connection is None:
        return None
    if connection.workspace_id is not None:
        return await db.get(Workspace, connection.workspace_id)
    if connection.user_id is None:
        return None
    member = await db.scalar(
        select(WorkspaceMember)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            WorkspaceMember.user_id == connection.user_id,
            Workspace.is_personal.is_(True),
        )
    )
    if member:
        return await db.get(Workspace, member.workspace_id)
    return None


async def _upsert_repository_for_workspace(
    db: AsyncSession,
    *,
    workspace: Workspace,
    connection: GitHubConnection | None,
    repo_data: dict[str, Any],
    context: dict[str, Any],
) -> Repository:
    logger.info(
        "process_pr_event stage=repository_upsert workspace_id=%d action=%s repo=%s pr_number=%s installation_id=%s",
        workspace.id,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
    repo = await db.scalar(
        select(Repository).where(
            Repository.workspace_id == workspace.id,
            Repository.github_id == repo_data["id"],
        )
    )
    if not repo:
        repo = Repository(
            workspace_id=workspace.id,
            github_connection_id=connection.id if connection else None,
            github_id=repo_data["id"],
            full_name=repo_data["full_name"],
            name=repo_data["name"],
        )
        db.add(repo)
        await db.flush()
    return repo


async def _upsert_pull_request_for_repository(
    db: AsyncSession,
    *,
    repo: Repository,
    pr_data: dict[str, Any],
    context: dict[str, Any],
) -> PullRequest:
    logger.info(
        "process_pr_event stage=pull_request_upsert workspace_id=%d action=%s repo=%s pr_number=%s installation_id=%s",
        repo.workspace_id,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
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
            state="merged" if pr_data.get("merged") else pr_data["state"],
            author=pr_data["user"]["login"],
            github_url=pr_data["html_url"],
            merged_at=_parse_github_datetime(pr_data.get("merged_at")),
        )
        db.add(pr)
    else:
        pr.title = pr_data["title"]
        pr.body = pr_data.get("body", "")
        pr.state = "merged" if pr_data.get("merged") else pr_data["state"]
        pr.github_url = pr_data["html_url"]
        pr.merged_at = _parse_github_datetime(pr_data.get("merged_at"))
    return pr


def _build_learning_extraction_request(
    *,
    workspace: Workspace,
    connection: GitHubConnection | None,
    pr: PullRequest,
    pr_dict: dict[str, Any],
    context: dict[str, Any],
) -> ExtractionRequest:
    return ExtractionRequest(
        workspace_id=workspace.id,
        pr_id=pr.id,
        created_by_user_id=connection.user_id if connection else None,
        repo=context["repo"],
        pr_number=pr.github_pr_number,
        installation_id=context["installation_id"],
        correlation_id=context.get("correlation_id"),
        pr_dict=pr_dict,
    )


async def _prepare_learning_extraction(
    *,
    workspace: Workspace,
    connection: GitHubConnection | None,
    payload: dict[str, Any],
    repo_data: dict[str, Any],
    pr_data: dict[str, Any],
    pr: PullRequest,
    context: dict[str, Any],
) -> ExtractionRequest | None:
    logger.info(
        "process_pr_event stage=extraction_prepare workspace_id=%d action=%s repo=%s pr_number=%s installation_id=%s",
        workspace.id,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
    if pr.processed:
        logger.info(
            "PR already processed, skipping extraction workspace_id=%d repo=%s pr_number=%d installation_id=%s",
            workspace.id,
            context["repo"],
            pr.github_pr_number,
            context["installation_id"],
        )
        return

    if not settings.anthropic_api_key and not settings.ollama_base_url:
        logger.info(
            "Skipping extraction because no LLM provider is configured workspace_id=%d repo=%s pr_number=%d installation_id=%s",
            workspace.id,
            context["repo"],
            pr.github_pr_number,
            context["installation_id"],
        )
        return None

    review_comments = await _fetch_review_comments(payload, repo_data, pr_data)
    pr_dict = _build_pr_dict_from_payload(pr_data, repo_data, review_comments)
    logger.info(
        "process_pr_event prepared extraction workspace_id=%d repo=%s pr_number=%d installation_id=%s review_comment_count=%d",
        workspace.id,
        context["repo"],
        pr.github_pr_number,
        context["installation_id"],
        len(pr_dict["review_comments"]),
    )
    return _build_learning_extraction_request(
        workspace=workspace,
        connection=connection,
        pr=pr,
        pr_dict=pr_dict,
        context=context,
    )


async def process_pr_event(payload: dict[str, Any], db: AsyncSession) -> ExtractionRequest | None:
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})
    installation_id = payload.get("installation", {}).get("id")
    context = _webhook_context(payload)

    logger.info(
        "process_pr_event received action=%s repo=%s pr_number=%s installation_id=%s",
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )

    connection = None
    if installation_id:
        connection = await db.scalar(
            select(GitHubConnection).where(
                GitHubConnection.provider_type == "app",
                GitHubConnection.installation_id == installation_id,
                GitHubConnection.is_active.is_(True),
            )
        )

    logger.info(
        "process_pr_event stage=workspace_resolution action=%s repo=%s pr_number=%s installation_id=%s",
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
    workspace = await _resolve_workspace_for_connection(db, connection)
    if workspace is None:
        logger.warning(
            "Skipping webhook PR event because no workspace mapping was found action=%s repo=%s pr_number=%s installation_id=%s",
            context["action"],
            context["repo"],
            context["pr_number"],
            context["installation_id"],
        )
        return

    logger.info(
        "process_pr_event resolved workspace workspace_id=%d action=%s repo=%s pr_number=%s installation_id=%s",
        workspace.id,
        context["action"],
        context["repo"],
        context["pr_number"],
        context["installation_id"],
    )
    repo = await _upsert_repository_for_workspace(
        db,
        workspace=workspace,
        connection=connection,
        repo_data=repo_data,
        context=context,
    )
    pr = await _upsert_pull_request_for_repository(
        db,
        repo=repo,
        pr_data=pr_data,
        context=context,
    )

    await db.commit()
    await db.refresh(pr)

    return await _prepare_learning_extraction(
        workspace=workspace,
        connection=connection,
        payload=payload,
        repo_data=repo_data,
        pr_data=pr_data,
        pr=pr,
        context=context,
    )


async def _fetch_review_comments(
    payload: dict[str, Any],
    repo_data: dict[str, Any],
    pr_data: dict[str, Any],
) -> list[dict[str, Any]]:
    if not (settings.github_app_id and settings.github_private_key):
        return []

    try:
        installation_id = payload.get("installation", {}).get("id")
        if not installation_id:
            return []

        from app.github.auth import get_installation_token
        from app.github.client import GitHubClient

        token = await get_installation_token(installation_id)
        client = GitHubClient(token)
        owner, repo_name = repo_data["full_name"].split("/")
        return await client.get_review_comments(owner, repo_name, pr_data["number"])
    except Exception:
        logger.exception(
            "Failed to fetch review comments from GitHub API repo=%s pr_number=%s installation_id=%s",
            repo_data.get("full_name", ""),
            pr_data.get("number"),
            payload.get("installation", {}).get("id"),
        )
        return []
