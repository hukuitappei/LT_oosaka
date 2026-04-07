from datetime import datetime, timezone

from app.db.models import LearningItem, LearningReuseEvent, PullRequest, Repository, ReviewComment
from app.services.reuse_impact_metrics import build_reuse_impact_summary, reuse_event_has_recurrence


def test_reuse_event_has_recurrence_detects_overlapping_review_terms():
    repo = Repository(id=1, workspace_id=1, github_id=1, full_name="owner/repo", name="repo")
    source_pr = PullRequest(
        id=10,
        repository_id=repo.id,
        repository=repo,
        github_pr_number=10,
        title="Original validation fix",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/10",
        review_comments=[],
        learning_items=[],
    )
    target_pr = PullRequest(
        id=11,
        repository_id=repo.id,
        repository=repo,
        github_pr_number=11,
        title="Follow-up change",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/11",
        review_comments=[],
        learning_items=[],
    )
    source_item = LearningItem(
        id=4,
        workspace_id=1,
        pull_request_id=source_pr.id,
        pull_request=source_pr,
        schema_version="1.0",
        title="Validate payload before persistence",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="Add payload validation",
        evidence="Reviewer asked for payload validation",
        status="applied",
        visibility="workspace_shared",
    )
    source_pr.learning_items = [source_item]
    target_pr.review_comments = [
        ReviewComment(
            pull_request_id=target_pr.id,
            github_comment_id=7001,
            author="reviewer",
            body="Please validate the payload earlier",
            diff_hunk=None,
            file_path="api/validators.py",
            line_number=5,
        )
    ]
    event = LearningReuseEvent(
        workspace_id=1,
        source_learning_item_id=source_item.id,
        source_learning_item=source_item,
        target_pull_request_id=target_pr.id,
        target_pull_request=target_pr,
        created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
    )

    assert reuse_event_has_recurrence(event) is True


def test_build_reuse_impact_summary_counts_recurring_and_clean_events():
    repo = Repository(id=1, workspace_id=1, github_id=1, full_name="owner/repo", name="repo")
    source_pr = PullRequest(
        id=10,
        repository_id=repo.id,
        repository=repo,
        github_pr_number=10,
        title="Original validation fix",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/10",
        review_comments=[],
        learning_items=[],
    )
    source_item = LearningItem(
        id=4,
        workspace_id=1,
        pull_request_id=10,
        pull_request=source_pr,
        schema_version="1.0",
        title="Validate payload before persistence",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="Add payload validation",
        evidence="Reviewer asked for payload validation",
        status="applied",
        visibility="workspace_shared",
    )
    source_pr.learning_items = [source_item]
    recurring_target_pr = PullRequest(
        id=11,
        repository_id=repo.id,
        repository=repo,
        github_pr_number=11,
        title="Follow-up change",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/11",
        review_comments=[
            ReviewComment(
                pull_request_id=11,
                github_comment_id=7002,
                author="reviewer",
                body="validate payload",
                diff_hunk=None,
                file_path=None,
                line_number=6,
            )
        ],
        learning_items=[],
    )
    clean_target_pr = PullRequest(
        id=12,
        repository_id=repo.id,
        repository=repo,
        github_pr_number=12,
        title="Rename helper",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/12",
        review_comments=[
            ReviewComment(
                pull_request_id=12,
                github_comment_id=7003,
                author="reviewer",
                body="rename helper method",
                diff_hunk=None,
                file_path="app/helpers.py",
                line_number=7,
            )
        ],
        learning_items=[],
    )
    recurring_event = LearningReuseEvent(
        workspace_id=1,
        source_learning_item_id=source_item.id,
        source_learning_item=source_item,
        target_pull_request_id=11,
        target_pull_request=recurring_target_pr,
        created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
    )
    clean_event = LearningReuseEvent(
        workspace_id=1,
        source_learning_item_id=source_item.id,
        source_learning_item=source_item,
        target_pull_request_id=12,
        target_pull_request=clean_target_pr,
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
    )

    summary = build_reuse_impact_summary([recurring_event, clean_event])

    assert summary.total_reuse_events == 2
    assert summary.reused_learning_items_count == 1
    assert summary.recurring_reuse_events == 1
    assert summary.clean_reuse_events == 1
