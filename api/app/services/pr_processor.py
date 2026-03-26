import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Repository, PullRequest
from app.config import settings

logger = logging.getLogger(__name__)


def _build_pr_dict_from_payload(
    pr_data: dict[str, Any],
    repo_data: dict[str, Any],
    review_comments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Webhook ペイロードから extractor 用の PR データを構築する"""
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


async def process_pr_event(payload: dict[str, Any], db: AsyncSession) -> None:
    """Webhook イベントから PR データを DB に保存し、学び抽出を試みる"""
    repo_data = payload.get("repository", {})
    pr_data = payload.get("pull_request", {})

    # --- Repository の upsert ---
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

    # --- PullRequest の upsert ---
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
        await db.flush()

    await db.commit()
    await db.refresh(pr)

    # --- 学び抽出（GitHub App + LLM が設定済みの場合のみ）---
    if not settings.anthropic_api_key and not settings.ollama_base_url:
        return

    try:
        review_comments = await _fetch_review_comments(payload, repo_data, pr_data)
        pr_dict = _build_pr_dict_from_payload(pr_data, repo_data, review_comments)

        from app.services.extractor import extract_from_pr
        from app.services.learning_saver import save_learning_items

        if settings.anthropic_api_key:
            from app.llm.anthropic_provider import AnthropicProvider
            provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        else:
            from app.llm.ollama_provider import OllamaProvider
            provider = OllamaProvider(host=settings.ollama_base_url)

        result = await extract_from_pr(pr_dict, provider)
        await save_learning_items(result, pr.id, db)
        logger.info("Extracted %d learning items for PR #%d", len(result.learning_items), pr.github_pr_number)

    except Exception:
        logger.exception("Learning extraction failed for PR #%d", pr_data.get("number"))


async def _fetch_review_comments(
    payload: dict[str, Any],
    repo_data: dict[str, Any],
    pr_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """GitHub API からレビューコメントを取得する（App 設定済みの場合）"""
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
        logger.exception("Failed to fetch review comments from GitHub API")
        return []
