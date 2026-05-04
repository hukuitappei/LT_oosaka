import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import LearningItem, PullRequest, Repository, ReviewComment, User, WeeklyDigest, Workspace, WorkspaceMember


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_build_retention_cleanup_window_uses_utc_now():
    from app.services.retention import build_retention_cleanup_window

    window = build_retention_cleanup_window(
        as_of=_aware(datetime(2026, 4, 7, 9, 0, 0)),
        pr_retention_days=90,
        log_retention_days=30,
        learning_retention_days=365,
        digest_retention_days=180,
    )

    assert window.pr_source_cutoff == _aware(datetime(2026, 1, 7, 9, 0, 0))
    assert window.log_metadata_cutoff == _aware(datetime(2026, 3, 8, 9, 0, 0))
    assert window.learning_cutoff == _aware(datetime(2025, 4, 7, 9, 0, 0))
    assert window.digest_cutoff == _aware(datetime(2025, 10, 9, 9, 0, 0))


@pytest.mark.asyncio
async def test_cleanup_expired_pr_source_data_deletes_expired_prs_and_related_rows(db_session):
    from app.services.retention import cleanup_expired_pr_source_data

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=101, full_name="acme/old", name="old")
    db_session.add(repo)
    await db_session.flush()

    old_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=7,
        title="Old PR",
        body="old body",
        state="closed",
        author="alice",
        github_url="https://github.com/acme/old/pull/7",
        created_at=_aware(datetime(2025, 12, 1, 12, 0, 0)),
    )
    recent_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=8,
        title="Recent PR",
        body="recent body",
        state="open",
        author="bob",
        github_url="https://github.com/acme/old/pull/8",
        created_at=_aware(datetime(2026, 3, 15, 12, 0, 0)),
    )
    db_session.add_all([old_pr, recent_pr])
    await db_session.flush()

    db_session.add_all(
        [
            ReviewComment(
                pull_request_id=old_pr.id,
                github_comment_id=1001,
                author="reviewer",
                body="Expired review note",
                file_path="app.py",
                line_number=10,
                diff_hunk="@@ -1 +1 @@",
                created_at=_aware(datetime(2025, 12, 2, 12, 0, 0)),
            ),
            ReviewComment(
                pull_request_id=recent_pr.id,
                github_comment_id=1002,
                author="reviewer",
                body="Keep this",
                file_path="app.py",
                line_number=11,
                diff_hunk="@@ -2 +2 @@",
                created_at=_aware(datetime(2026, 3, 16, 12, 0, 0)),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=old_pr.id,
                created_by_user_id=owner.id,
                visibility="workspace_shared",
                schema_version="1.0",
                title="Old lesson",
                detail="This should be purged with the PR source data.",
                category="quality",
                confidence=0.9,
                action_for_next_time="Add validation.",
                evidence="Old review comment.",
                created_at=_aware(datetime(2025, 12, 3, 12, 0, 0)),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=recent_pr.id,
                created_by_user_id=owner.id,
                visibility="workspace_shared",
                schema_version="1.0",
                title="Recent lesson",
                detail="This should remain.",
                category="quality",
                confidence=0.8,
                action_for_next_time="Keep checking.",
                evidence="Recent review comment.",
                created_at=_aware(datetime(2026, 4, 1, 12, 0, 0)),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=recent_pr.id,
                created_by_user_id=owner.id,
                visibility="workspace_shared",
                schema_version="1.0",
                title="Old independent lesson",
                detail="This should be removed by learning retention.",
                category="quality",
                confidence=0.7,
                action_for_next_time="Keep records short.",
                evidence="Recent PR but stale learning item.",
                created_at=_aware(datetime(2026, 3, 1, 12, 0, 0)),
            ),
            WeeklyDigest(
                workspace_id=workspace.id,
                year=2025,
                week=48,
                summary="Old digest",
                repeated_issues=["validation"],
                next_time_notes=["archive"],
                pr_count=1,
                learning_count=1,
                created_at=_aware(datetime(2025, 12, 5, 12, 0, 0)),
            ),
            WeeklyDigest(
                workspace_id=workspace.id,
                year=2026,
                week=14,
                summary="Recent digest",
                repeated_issues=["tests"],
                next_time_notes=["keep"],
                pr_count=1,
                learning_count=1,
                created_at=_aware(datetime(2026, 4, 1, 12, 0, 0)),
            ),
        ]
    )
    await db_session.commit()

    result = await cleanup_expired_pr_source_data(
        db_session,
        as_of=_aware(datetime(2026, 4, 7, 9, 0, 0)),
        pr_retention_days=90,
        log_retention_days=30,
        learning_retention_days=20,
        digest_retention_days=100,
    )

    assert result.expired_pull_request_ids == (old_pr.id,)
    assert len(result.expired_learning_item_ids) == 1
    assert result.deleted_pull_requests == 1
    assert result.deleted_review_comments == 1
    assert result.detached_learning_items == 1
    assert result.deleted_expired_learning_items == 1
    assert result.deleted_weekly_digests == 1
    assert result.deleted_source_rows == 5
    assert result.window.pr_source_cutoff == _aware(datetime(2026, 1, 7, 9, 0, 0))
    assert result.window.log_metadata_cutoff == _aware(datetime(2026, 3, 8, 9, 0, 0))
    assert result.window.learning_cutoff == _aware(datetime(2026, 3, 18, 9, 0, 0))
    assert result.window.digest_cutoff == _aware(datetime(2025, 12, 28, 9, 0, 0))

    assert await db_session.scalar(select(PullRequest).where(PullRequest.id == old_pr.id)) is None
    assert await db_session.scalar(select(ReviewComment).where(ReviewComment.pull_request_id == old_pr.id)) is None
    detached_items = list(
        (await db_session.scalars(select(LearningItem).where(LearningItem.pull_request_id.is_(None)))).all()
    )
    assert any(item.title == "Old lesson" for item in detached_items)
    assert await db_session.scalar(select(PullRequest).where(PullRequest.id == recent_pr.id)) is not None
    assert await db_session.scalar(select(ReviewComment).where(ReviewComment.pull_request_id == recent_pr.id)) is not None
    remaining_learning_items = list(
        (await db_session.scalars(select(LearningItem).where(LearningItem.pull_request_id == recent_pr.id))).all()
    )
    assert len(remaining_learning_items) == 1
    assert await db_session.scalar(select(Repository).where(Repository.id == repo.id)) is not None
    assert await db_session.scalar(select(WeeklyDigest).where(WeeklyDigest.year == 2025, WeeklyDigest.week == 48)) is None
    assert await db_session.scalar(select(WeeklyDigest).where(WeeklyDigest.year == 2026, WeeklyDigest.week == 14)) is not None


@pytest.mark.asyncio
async def test_cleanup_expired_pr_source_data_is_noop_when_nothing_is_expired(db_session):
    from app.services.retention import cleanup_expired_pr_source_data

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=202, full_name="acme/current", name="current")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=9,
        title="Current PR",
        body="current body",
        state="open",
        author="carol",
        github_url="https://github.com/acme/current/pull/9",
        created_at=_aware(datetime(2026, 4, 1, 12, 0, 0)),
    )
    db_session.add(pr)
    await db_session.commit()

    result = await cleanup_expired_pr_source_data(
        db_session,
        as_of=_aware(datetime(2026, 4, 7, 9, 0, 0)),
        pr_retention_days=90,
        log_retention_days=30,
        learning_retention_days=365,
        digest_retention_days=365,
    )

    assert result.expired_pull_request_ids == ()
    assert result.expired_learning_item_ids == ()
    assert result.deleted_source_rows == 0
    assert await db_session.scalar(select(PullRequest).where(PullRequest.id == pr.id)) is not None
