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
