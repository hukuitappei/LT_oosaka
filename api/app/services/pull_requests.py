from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LearningItem, PullRequest, Repository

logger = logging.getLogger(__name__)


class PullRequestNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class RelatedLearningItemMatch:
    item: LearningItem
    matched_terms: list[str]
    same_repository: bool
    score: int


TOKEN_RE = re.compile(r"[a-z0-9_]{4,}")
STOP_WORDS = {
    "this",
    "that",
    "with",
    "from",
    "into",
    "before",
    "after",
    "should",
    "would",
    "could",
    "there",
    "their",
    "about",
    "review",
    "request",
    "pull",
    "github",
    "have",
    "were",
    "when",
    "where",
    "validation",
}


def _tokenize(*values: str | None) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        if not value:
            continue
        for token in TOKEN_RE.findall(value.lower()):
            if token not in STOP_WORDS:
                tokens.add(token)
    return tokens


def _build_pr_context_tokens(pr: PullRequest) -> set[str]:
    learning_tokens: set[str] = set()
    for item in pr.learning_items:
        learning_tokens |= _tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
        )

    return _tokenize(
        pr.title,
        pr.body,
        pr.author,
        pr.repository.full_name if pr.repository else None,
    ) | learning_tokens


def _score_related_learning_items(
    pr: PullRequest,
    candidates: list[LearningItem],
) -> list[RelatedLearningItemMatch]:
    context_tokens = _build_pr_context_tokens(pr)
    if not context_tokens:
        return []

    matches: list[RelatedLearningItemMatch] = []
    for item in candidates:
        candidate_tokens = _tokenize(
            item.title,
            item.detail,
            item.evidence,
            item.action_for_next_time,
            item.category,
            item.pull_request.title if item.pull_request else None,
            item.pull_request.repository.full_name if item.pull_request and item.pull_request.repository else None,
        )
        matched_terms = sorted(context_tokens & candidate_tokens)
        if not matched_terms:
            continue

        same_repository = (
            pr.repository is not None
            and item.pull_request is not None
            and item.pull_request.repository is not None
            and item.pull_request.repository.id == pr.repository.id
        )
        if not same_repository and len(matched_terms) < 2:
            continue
        score = len(matched_terms) + (2 if same_repository else 0) + int(item.status != "ignored")
        matches.append(
            RelatedLearningItemMatch(
                item=item,
                matched_terms=matched_terms[:5],
                same_repository=same_repository,
                score=score,
            )
        )

    matches.sort(
        key=lambda match: (
            -match.score,
            match.item.status == "ignored",
            -match.item.confidence,
            -match.item.id,
        )
    )
    return matches[:3]


async def get_workspace_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
) -> PullRequest | None:
    return await db.scalar(
        select(PullRequest)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(PullRequest.learning_items),
            selectinload(PullRequest.repository),
        )
        .where(PullRequest.id == pr_id, Repository.workspace_id == workspace_id)
    )


async def get_related_learning_items_for_pull_request(
    db: AsyncSession,
    pr: PullRequest,
    workspace_id: int,
) -> list[RelatedLearningItemMatch]:
    result = await db.execute(
        select(LearningItem)
        .join(PullRequest, LearningItem.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .options(
            selectinload(LearningItem.pull_request).selectinload(PullRequest.repository),
        )
        .where(
            LearningItem.workspace_id == workspace_id,
            LearningItem.pull_request_id != pr.id,
        )
        .order_by(LearningItem.created_at.desc())
    )
    return _score_related_learning_items(pr, list(result.scalars().all()))


async def request_reanalysis_for_pull_request(
    db: AsyncSession,
    pr_id: int,
    workspace_id: int,
    user_id: int,
) -> dict[str, int | str]:
    pr = await get_workspace_pull_request(db, pr_id, workspace_id)
    if not pr:
        raise PullRequestNotFoundError

    from app.tasks.extract import reanalyze_pr_task

    reanalyze_pr_task.delay(pr.id, workspace_id, user_id)
    logger.info(
        "request_reanalysis_for_pull_request enqueued pr_id=%d workspace_id=%d user_id=%d",
        pr.id,
        workspace_id,
        user_id,
    )
    return {"status": "accepted", "pr_id": pr_id}
