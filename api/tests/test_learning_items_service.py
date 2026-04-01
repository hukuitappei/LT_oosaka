from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_list_workspace_learning_items_applies_filters(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.learning_items import list_workspace_learning_items

    workspace = Workspace(name="Alpha", slug="alpha", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve validation",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/42",
    )
    db_session.add(pr)
    await db_session.flush()

    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=pr.id,
                schema_version="1.0",
                title="Design item",
                detail="detail",
                category="design",
                confidence=0.9,
                action_for_next_time="act",
                evidence="evidence",
                status="new",
                visibility="workspace_shared",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=pr.id,
                schema_version="1.0",
                title="Other item",
                detail="detail",
                category="testing",
                confidence=0.8,
                action_for_next_time="act",
                evidence="review found flaky coverage",
                status="applied",
                visibility="private_draft",
                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
        ]
    )
    await db_session.commit()

    items = await list_workspace_learning_items(
        db_session,
        workspace.id,
        q="design",
        category="design",
        status="new",
        visibility="workspace_shared",
    )

    assert [item.title for item in items] == ["Design item"]
    assert items[0].repository.full_name == "owner/repo"
    assert items[0].pull_request.github_pr_number == 42
    assert items[0].status == "new"


@pytest.mark.asyncio
async def test_get_workspace_learning_item_requires_workspace_scope(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.learning_items import (
        LearningItemNotFoundError,
        get_workspace_learning_item,
    )

    workspace = Workspace(name="Alpha", slug="alpha", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve validation",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/42",
    )
    db_session.add(pr)
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="Design item",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        status="new",
        visibility="workspace_shared",
    )
    db_session.add(item)
    await db_session.commit()

    found = await get_workspace_learning_item(db_session, item.id, workspace.id)
    assert found.id == item.id

    with pytest.raises(LearningItemNotFoundError):
        await get_workspace_learning_item(db_session, item.id, workspace.id + 1)


@pytest.mark.asyncio
async def test_update_workspace_learning_item_updates_status_and_visibility(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.learning_items import update_workspace_learning_item

    workspace = Workspace(name="Alpha", slug="alpha-update", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve validation",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/42",
    )
    db_session.add(pr)
    await db_session.flush()

    item = LearningItem(
        workspace_id=workspace.id,
        pull_request_id=pr.id,
        schema_version="1.0",
        title="Design item",
        detail="detail",
        category="design",
        confidence=0.9,
        action_for_next_time="act",
        evidence="evidence",
        status="new",
        visibility="private_draft",
    )
    db_session.add(item)
    await db_session.commit()

    updated = await update_workspace_learning_item(
        db_session,
        item.id,
        workspace.id,
        status="applied",
        visibility="workspace_shared",
    )

    assert updated.status == "applied"
    assert updated.visibility == "workspace_shared"


@pytest.mark.asyncio
async def test_summarize_workspace_learning_items_returns_weekly_points(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.learning_items import summarize_workspace_learning_items

    workspace = Workspace(name="Alpha", slug="alpha-summary", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    first_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve validation",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/42",
        created_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
    )
    second_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=43,
        title="Improve tests",
        body="body",
        state="merged",
        author="alice",
        github_url="https://example.com/pr/43",
        created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
    )
    db_session.add_all([first_pr, second_pr])
    await db_session.flush()

    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=first_pr.id,
                schema_version="1.0",
                title="Design item",
                detail="detail",
                category="design",
                confidence=0.9,
                action_for_next_time="act",
                evidence="evidence",
                status="new",
                visibility="workspace_shared",
                created_at=datetime(2026, 3, 18, tzinfo=timezone.utc),
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=second_pr.id,
                schema_version="1.0",
                title="Testing item",
                detail="detail",
                category="testing",
                confidence=0.8,
                action_for_next_time="act",
                evidence="evidence",
                status="in_progress",
                visibility="workspace_shared",
                created_at=datetime(2026, 3, 25, tzinfo=timezone.utc),
            ),
        ]
    )
    await db_session.commit()

    summary = await summarize_workspace_learning_items(
        db_session,
        workspace.id,
        weeks=3,
        today=datetime(2026, 3, 27, tzinfo=timezone.utc).date(),
    )

    assert summary.total_learning_items == 2
    assert summary.current_week_count == 1
    assert [point.label for point in summary.weekly_points] == ["2026-W11", "2026-W12", "2026-W13"]
    assert [point.learning_count for point in summary.weekly_points] == [0, 1, 1]
    assert {(row.category, row.count) for row in summary.top_categories} == {("design", 1), ("testing", 1)}
    assert {(row.status, row.count) for row in summary.status_counts} == {
        ("new", 1),
        ("in_progress", 1),
        ("applied", 0),
        ("ignored", 0),
    }
