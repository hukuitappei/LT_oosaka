from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import LearningItem, PullRequest, ReviewComment, WeeklyDigest

DEFAULT_PR_RETENTION_DAYS = settings.pr_retention_days
DEFAULT_LOG_RETENTION_DAYS = settings.log_retention_days
DEFAULT_LEARNING_RETENTION_DAYS = settings.learning_retention_days
DEFAULT_DIGEST_RETENTION_DAYS = settings.digest_retention_days


@dataclass(frozen=True)
class RetentionCleanupWindow:
    as_of: datetime
    pr_source_cutoff: datetime
    log_metadata_cutoff: datetime
    learning_cutoff: datetime
    digest_cutoff: datetime


@dataclass(frozen=True)
class RetentionCleanupResult:
    window: RetentionCleanupWindow
    expired_pull_request_ids: tuple[int, ...]
    expired_learning_item_ids: tuple[int, ...]
    detached_learning_items: int
    deleted_expired_learning_items: int
    deleted_review_comments: int
    deleted_pull_requests: int
    deleted_weekly_digests: int

    @property
    def deleted_source_rows(self) -> int:
        return (
            self.detached_learning_items
            + self.deleted_expired_learning_items
            + self.deleted_review_comments
            + self.deleted_pull_requests
            + self.deleted_weekly_digests
        )


def build_retention_cleanup_window(
    *,
    as_of: datetime | None = None,
    pr_retention_days: int = DEFAULT_PR_RETENTION_DAYS,
    log_retention_days: int = DEFAULT_LOG_RETENTION_DAYS,
    learning_retention_days: int = DEFAULT_LEARNING_RETENTION_DAYS,
    digest_retention_days: int = DEFAULT_DIGEST_RETENTION_DAYS,
) -> RetentionCleanupWindow:
    reference = as_of or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    pr_cutoff = reference - timedelta(days=pr_retention_days)
    log_cutoff = reference - timedelta(days=log_retention_days)
    learning_cutoff = reference - timedelta(days=learning_retention_days)
    digest_cutoff = reference - timedelta(days=digest_retention_days)
    return RetentionCleanupWindow(
        as_of=reference,
        pr_source_cutoff=pr_cutoff,
        log_metadata_cutoff=log_cutoff,
        learning_cutoff=learning_cutoff,
        digest_cutoff=digest_cutoff,
    )


async def cleanup_expired_pr_source_data(
    db: AsyncSession,
    *,
    as_of: datetime | None = None,
    pr_retention_days: int = DEFAULT_PR_RETENTION_DAYS,
    log_retention_days: int = DEFAULT_LOG_RETENTION_DAYS,
    learning_retention_days: int = DEFAULT_LEARNING_RETENTION_DAYS,
    digest_retention_days: int = DEFAULT_DIGEST_RETENTION_DAYS,
) -> RetentionCleanupResult:
    """
    Delete expired PR source data and keep a log-retention cutoff for downstream tasks.

    The repository currently does not persist application logs in the database, so the
    log-retention part of the cleanup is represented as a cutoff in the returned window.
    A scheduled task can use that cutoff later against an external log sink.
    """

    window = build_retention_cleanup_window(
        as_of=as_of,
        pr_retention_days=pr_retention_days,
        log_retention_days=log_retention_days,
        learning_retention_days=learning_retention_days,
        digest_retention_days=digest_retention_days,
    )

    expired_pr_ids = tuple(
        await db.scalars(
            select(PullRequest.id).where(PullRequest.created_at < window.pr_source_cutoff)
        )
    )
    if not expired_pr_ids:
        return RetentionCleanupResult(
            window=window,
            expired_pull_request_ids=(),
            expired_learning_item_ids=(),
            detached_learning_items=0,
            deleted_expired_learning_items=0,
            deleted_review_comments=0,
            deleted_pull_requests=0,
            deleted_weekly_digests=0,
        )

    learning_item_query = select(LearningItem.id).where(LearningItem.created_at < window.learning_cutoff)
    if expired_pr_ids:
        learning_item_query = learning_item_query.where(
            or_(
                LearningItem.pull_request_id.is_(None),
                ~LearningItem.pull_request_id.in_(expired_pr_ids),
            )
        )
    expired_learning_item_ids = tuple(await db.scalars(learning_item_query))

    deleted_expired_learning_items = 0
    if expired_learning_item_ids:
        deleted_expired_learning_items = (
            await db.execute(delete(LearningItem).where(LearningItem.id.in_(expired_learning_item_ids)))
        ).rowcount or 0

    detached_learning_items = (
        await db.execute(
            update(LearningItem)
            .where(LearningItem.pull_request_id.in_(expired_pr_ids))
            .values(pull_request_id=None)
        )
    ).rowcount or 0
    deleted_review_comments = (
        await db.execute(
            delete(ReviewComment).where(ReviewComment.pull_request_id.in_(expired_pr_ids))
        )
    ).rowcount or 0
    deleted_pull_requests = (
        await db.execute(delete(PullRequest).where(PullRequest.id.in_(expired_pr_ids)))
    ).rowcount or 0
    deleted_weekly_digests = (
        await db.execute(delete(WeeklyDigest).where(WeeklyDigest.created_at < window.digest_cutoff))
    ).rowcount or 0
    await db.commit()

    return RetentionCleanupResult(
        window=window,
        expired_pull_request_ids=expired_pr_ids,
        expired_learning_item_ids=expired_learning_item_ids,
        detached_learning_items=detached_learning_items,
        deleted_expired_learning_items=deleted_expired_learning_items,
        deleted_review_comments=deleted_review_comments,
        deleted_pull_requests=deleted_pull_requests,
        deleted_weekly_digests=deleted_weekly_digests,
    )
