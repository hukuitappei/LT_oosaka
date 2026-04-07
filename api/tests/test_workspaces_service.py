import sys
from pathlib import Path

import pytest
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import (
    GitHubConnection,
    LearningItem,
    PullRequest,
    Repository,
    ReviewComment,
    User,
    WeeklyDigest,
    Workspace,
    WorkspaceMember,
)


@pytest.mark.asyncio
async def test_list_user_workspaces_returns_roles_in_order(db_session):
    from app.services.workspaces import list_user_workspaces

    user = User(email="owner@example.com", hashed_password="hashed::pw")
    db_session.add(user)
    await db_session.flush()

    personal = Workspace(name="Personal", slug="personal", is_personal=True)
    team = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([personal, team])
    await db_session.flush()

    db_session.add_all(
        [
            WorkspaceMember(workspace_id=team.id, user_id=user.id, role="admin"),
            WorkspaceMember(workspace_id=personal.id, user_id=user.id, role="owner"),
        ]
    )
    await db_session.commit()

    result = await list_user_workspaces(db_session, user.id)

    assert [(workspace.name, role) for workspace, role in result] == [
        ("Personal", "owner"),
        ("Alpha", "admin"),
    ]


@pytest.mark.asyncio
async def test_get_user_workspace_requires_membership(db_session):
    from app.services.workspaces import WorkspaceNotFoundError, get_user_workspace

    user = User(email="member@example.com", hashed_password="hashed::pw")
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))
    await db_session.commit()

    found_workspace, role = await get_user_workspace(db_session, workspace.id, user.id)
    assert found_workspace.id == workspace.id
    assert role == "member"

    with pytest.raises(WorkspaceNotFoundError):
        await get_user_workspace(db_session, workspace.id, user.id + 100)


@pytest.mark.asyncio
async def test_add_workspace_member_by_email_creates_membership(db_session):
    from app.services.workspaces import add_workspace_member_by_email

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    member = User(email="member@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, member, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.commit()

    await add_workspace_member_by_email(db_session, workspace.id, member.email, "member")

    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == member.id,
        )
    )
    assert membership is not None
    assert membership.role == "member"


@pytest.mark.asyncio
async def test_update_workspace_member_role_updates_existing_member(db_session):
    from app.services.workspaces import update_workspace_member_role

    user = User(email="member@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([user, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="member"))
    await db_session.commit()

    await update_workspace_member_role(db_session, workspace.id, user.id, "admin")

    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    assert membership is not None
    assert membership.role == "admin"


@pytest.mark.asyncio
async def test_add_workspace_member_to_workspace_requires_admin_membership(db_session):
    from app.services.workspaces import WorkspacePermissionError, add_workspace_member_to_workspace

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    member = User(email="member@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, member, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="member"))
    await db_session.commit()

    with pytest.raises(WorkspacePermissionError):
        await add_workspace_member_to_workspace(
            db_session,
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            email=member.email,
            role="member",
        )


@pytest.mark.asyncio
async def test_update_workspace_member_role_in_workspace_updates_member_when_admin(db_session):
    from app.services.workspaces import update_workspace_member_role_in_workspace

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    target = User(email="target@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, target, workspace])
    await db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="admin"),
            WorkspaceMember(workspace_id=workspace.id, user_id=target.id, role="member"),
        ]
    )
    await db_session.commit()

    await update_workspace_member_role_in_workspace(
        db_session,
        workspace_id=workspace.id,
        actor_user_id=owner.id,
        target_user_id=target.id,
        role="owner",
    )

    membership = await db_session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == target.id,
        )
    )
    assert membership is not None
    assert membership.role == "owner"


@pytest.mark.asyncio
async def test_purge_workspace_deletes_workspace_scoped_data(db_session):
    from app.services.workspaces import purge_workspace

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, workspace])
    await db_session.flush()
    db_session.add(WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"))
    await db_session.flush()

    repo = Repository(workspace_id=workspace.id, github_id=1, full_name="acme/repo", name="repo")
    db_session.add(repo)
    await db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Improve flow",
        body="body",
        state="merged",
        author="alice",
        github_url="https://github.com/acme/repo/pull/42",
    )
    db_session.add(pr)
    await db_session.flush()

    db_session.add_all(
        [
            ReviewComment(
                pull_request_id=pr.id,
                github_comment_id=1001,
                author="reviewer",
                body="Looks fine",
                file_path="app.py",
                line_number=12,
                diff_hunk="@@ -1 +1 @@",
            ),
            LearningItem(
                workspace_id=workspace.id,
                pull_request_id=pr.id,
                created_by_user_id=owner.id,
                visibility="workspace_shared",
                schema_version="1.0",
                title="Check validation",
                detail="Validate input before saving.",
                category="quality",
                confidence=0.8,
                action_for_next_time="Add request validation.",
                evidence="Review asked for validation.",
            ),
            WeeklyDigest(
                workspace_id=workspace.id,
                visibility="workspace_shared",
                year=2026,
                week=13,
                summary="summary",
                repeated_issues=[],
                next_time_notes=[],
                pr_count=1,
                learning_count=1,
            ),
            GitHubConnection(
                provider_type="token",
                workspace_id=workspace.id,
                user_id=owner.id,
                access_token="secret",
            ),
        ]
    )
    await db_session.commit()

    result = await purge_workspace(
        db_session,
        workspace_id=workspace.id,
        actor_user_id=owner.id,
        confirm_slug="alpha",
    )

    assert result.workspace_id == workspace.id
    assert result.deleted_learning_items == 1
    assert result.deleted_review_comments == 1
    assert result.deleted_pull_requests == 1
    assert result.deleted_repositories == 1
    assert result.deleted_weekly_digests == 1
    assert result.deleted_github_connections == 1
    assert result.deleted_memberships == 1

    assert await db_session.get(Workspace, workspace.id) is None
    assert await db_session.scalar(select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)) is None
    assert await db_session.scalar(select(Repository).where(Repository.workspace_id == workspace.id)) is None
    assert await db_session.scalar(select(PullRequest).where(PullRequest.repository_id == repo.id)) is None
    assert await db_session.scalar(select(ReviewComment).where(ReviewComment.pull_request_id == pr.id)) is None
    assert await db_session.scalar(select(LearningItem).where(LearningItem.workspace_id == workspace.id)) is None
    assert await db_session.scalar(select(WeeklyDigest).where(WeeklyDigest.workspace_id == workspace.id)) is None
    assert await db_session.scalar(select(GitHubConnection).where(GitHubConnection.workspace_id == workspace.id)) is None


@pytest.mark.asyncio
async def test_purge_workspace_requires_owner_and_confirmation(db_session):
    from app.services.workspaces import (
        WorkspaceDeleteConfirmationError,
        WorkspaceDeletePermissionError,
        purge_workspace,
    )

    owner = User(email="owner@example.com", hashed_password="hashed::pw")
    member = User(email="member@example.com", hashed_password="hashed::pw")
    workspace = Workspace(name="Alpha", slug="alpha", is_personal=False)
    db_session.add_all([owner, member, workspace])
    await db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(workspace_id=workspace.id, user_id=owner.id, role="owner"),
            WorkspaceMember(workspace_id=workspace.id, user_id=member.id, role="member"),
        ]
    )
    await db_session.commit()

    with pytest.raises(WorkspaceDeleteConfirmationError):
        await purge_workspace(
            db_session,
            workspace_id=workspace.id,
            actor_user_id=owner.id,
            confirm_slug="wrong",
        )

    with pytest.raises(WorkspaceDeletePermissionError):
        await purge_workspace(
            db_session,
            workspace_id=workspace.id,
            actor_user_id=member.id,
            confirm_slug="alpha",
        )
