from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_list_workspace_repositories_returns_workspace_rows(db_session):
    from app.db.models import Repository
    from app.services.repositories import list_workspace_repositories

    db_session.add_all(
        [
            Repository(
                workspace_id=1,
                github_id=1,
                full_name="owner/older",
                name="older",
                created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            ),
            Repository(
                workspace_id=1,
                github_id=2,
                full_name="owner/newer",
                name="newer",
                created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
            ),
            Repository(
                workspace_id=2,
                github_id=3,
                full_name="other/repo",
                name="repo",
                created_at=datetime(2026, 3, 3, tzinfo=timezone.utc),
            ),
        ]
    )
    await db_session.commit()

    repos = await list_workspace_repositories(db_session, 1)

    assert [repo.full_name for repo in repos] == ["owner/newer", "owner/older"]


@pytest.mark.asyncio
async def test_list_workspace_repository_pull_requests_requires_workspace_repo(db_session):
    from app.db.models import PullRequest, Repository
    from app.services.repositories import (
        RepositoryNotFoundError,
        list_workspace_repository_pull_requests,
    )

    repo = Repository(workspace_id=1, github_id=1, full_name="owner/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()
    db_session.add(
        PullRequest(
            repository_id=repo.id,
            github_pr_number=42,
            title="title",
            body="body",
            state="merged",
            author="alice",
            github_url="https://example.com/pr/42",
        )
    )
    await db_session.commit()

    prs = await list_workspace_repository_pull_requests(db_session, repo.id, 1)
    assert len(prs) == 1
    assert prs[0].github_pr_number == 42

    with pytest.raises(RepositoryNotFoundError):
        await list_workspace_repository_pull_requests(db_session, repo.id, 2)
