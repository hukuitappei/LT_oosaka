import sys
from pathlib import Path

import pytest
from sqlalchemy import select

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.models import User, Workspace, WorkspaceMember


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
