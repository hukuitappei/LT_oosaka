from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_get_workspace_pull_request_returns_workspace_pr(db_session):
    from app.db.models import PullRequest, Repository, Workspace
    from app.services.pull_requests import get_workspace_pull_request

    workspace = Workspace(name="ws", slug="ws", is_personal=True)
    other_workspace = Workspace(name="other", slug="other", is_personal=True)
    db_session.add_all([workspace, other_workspace])
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="title",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com",
    )
    db_session.add(pr)
    await db_session.commit()

    found = await get_workspace_pull_request(db_session, pr.id, workspace.id)
    not_found = await get_workspace_pull_request(db_session, pr.id, other_workspace.id)

    assert found is not None
    assert found.id == pr.id
    assert not_found is None


@pytest.mark.asyncio
async def test_request_reanalysis_for_pull_request_enqueues_task(monkeypatch, db_session):
    from app.db.models import PullRequest, Repository, Workspace
    from app.services.pull_requests import request_reanalysis_for_pull_request

    workspace = Workspace(name="ws", slug="ws", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="title",
        body="body",
        state="merged",
        author="author",
        github_url="https://example.com",
    )
    db_session.add(pr)
    await db_session.commit()

    delay_mock = MagicMock()
    monkeypatch.setattr("app.tasks.extract.reanalyze_pr_task.delay", delay_mock)

    result = await request_reanalysis_for_pull_request(db_session, pr.id, workspace.id, 7)

    assert result == {"status": "accepted", "pr_id": pr.id}
    delay_mock.assert_called_once_with(pr.id, workspace.id, 7)


@pytest.mark.asyncio
async def test_get_related_learning_items_for_pull_request_returns_ranked_matches(db_session):
    from app.db.models import LearningItem, PullRequest, Repository, Workspace
    from app.services.pull_requests import (
        get_related_learning_items_for_pull_request,
        get_workspace_pull_request,
    )

    workspace = Workspace(name="ws", slug="ws-related", is_personal=True)
    db_session.add(workspace)
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="owner/repo", name="repo")
    other_repo = Repository(workspace_id=workspace.id, github_id=2, full_name="owner/other", name="other")
    db_session.add_all([repo, other_repo])
    await db_session.flush()

    current_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=1,
        title="Tighten request validation and persistence boundaries",
        body="Validation should happen before persistence in the API layer.",
        state="merged",
        author="author",
        github_url="https://example.com/pr/1",
    )
    related_pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=2,
        title="Add validation to API boundary",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/2",
    )
    weaker_pr = PullRequest(
        repository_id=other_repo.id,
        github_pr_number=3,
        title="Improve test fixtures",
        body="Body",
        state="merged",
        author="author",
        github_url="https://example.com/pr/3",
    )
    db_session.add_all([current_pr, related_pr, weaker_pr])
    await db_session.flush()

    db_session.add_all(
        [
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=current_pr.id,
                schema_version="1.0",
                title="Current item",
                detail="detail",
                category="design",
                confidence=0.9,
                action_for_next_time="act",
                evidence="evidence",
                status="new",
                visibility="workspace_shared",
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=related_pr.id,
                schema_version="1.0",
                title="Validate before persistence",
                detail="Move validation into the API layer before saving records.",
                category="design",
                confidence=0.95,
                action_for_next_time="Check boundaries first.",
                evidence="Review flagged missing validation before persistence.",
                status="applied",
                visibility="workspace_shared",
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=weaker_pr.id,
                schema_version="1.0",
                title="Improve fixtures",
                detail="Keep fixture setup isolated for tests.",
                category="testing",
                confidence=0.7,
                action_for_next_time="act",
                evidence="test fixture issue",
                status="new",
                visibility="workspace_shared",
            ),
        ]
    )
    await db_session.commit()

    pr = await get_workspace_pull_request(db_session, current_pr.id, workspace.id)
    assert pr is not None

    matches = await get_related_learning_items_for_pull_request(db_session, pr, workspace.id)

    assert len(matches) == 1
    assert matches[0].item.pull_request_id == related_pr.id
    assert matches[0].same_repository is True
    assert "persistence" in matches[0].matched_terms
