import pytest


@pytest.mark.asyncio
async def test_list_user_github_connections_returns_workspace_and_personal_rows(db_session):
    from app.db.models import GitHubConnection, User, Workspace
    from app.services.github_connections import list_user_github_connections

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()

    db_session.add_all(
        [
            GitHubConnection(provider_type="app", workspace_id=workspace.id, user_id=user.id, installation_id=1),
            GitHubConnection(provider_type="token", workspace_id=None, user_id=user.id, access_token="secret"),
        ]
    )
    await db_session.commit()

    rows = await list_user_github_connections(
        db_session,
        current_user_id=user.id,
        current_workspace_id=workspace.id,
    )

    assert len(rows) == 2


@pytest.mark.asyncio
async def test_link_app_github_connection_reuses_existing_row(db_session):
    from app.db.models import GitHubConnection, User, Workspace
    from app.services.github_connections import link_app_github_connection

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha-gh", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()

    existing = GitHubConnection(
        provider_type="app",
        workspace_id=workspace.id,
        user_id=user.id,
        installation_id=123,
        is_active=False,
    )
    db_session.add(existing)
    await db_session.commit()

    connection = await link_app_github_connection(
        db_session,
        workspace_id=workspace.id,
        user_id=user.id,
        installation_id=123,
        github_account_login="octocat",
        label="main",
    )

    assert connection.id == existing.id
    assert connection.github_account_login == "octocat"
    assert connection.label == "main"
    assert connection.is_active is True
