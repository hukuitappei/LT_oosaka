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
                evidence="evidence",
                visibility="private_draft",
                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
        ]
    )
    await db_session.commit()

    items = await list_workspace_learning_items(
        db_session,
        workspace.id,
        category="design",
        visibility="workspace_shared",
    )

    assert [item.title for item in items] == ["Design item"]
    assert items[0].repository.full_name == "owner/repo"
    assert items[0].pull_request.github_pr_number == 42


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
        visibility="workspace_shared",
    )
    db_session.add(item)
    await db_session.commit()

    found = await get_workspace_learning_item(db_session, item.id, workspace.id)
    assert found.id == item.id

    with pytest.raises(LearningItemNotFoundError):
        await get_workspace_learning_item(db_session, item.id, workspace.id + 1)
