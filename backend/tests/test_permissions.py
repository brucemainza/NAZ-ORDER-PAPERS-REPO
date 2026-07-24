from datetime import datetime, timedelta, timezone

from app.lib.auth import create_access_token
from app.models import Permission, Role, User, UserSession
from app.services.permissions import DEFAULT_ROLE_PERMISSIONS, seed_default_roles


def make_user(db_session, employee_id, roles):
    user = User(
        employee_id=employee_id,
        name=f"User {employee_id}",
        role="Legacy",
        roles=roles,
        status="Active",
        password_hash=None,
    )
    db_session.add(user)
    db_session.flush()
    return user


def auth_headers(db_session, user):
    token, jti = create_access_token({"sub": str(user.id)})
    now = datetime.now(timezone.utc)
    db_session.add(
        UserSession(
            user_id=user.id,
            jti=jti,
            issued_at=now,
            expires_at=now + timedelta(hours=8),
        )
    )
    db_session.commit()
    return {"Authorization": f"Bearer {token}"}


def test_default_roles_are_seeded_with_configured_permissions(db_session):
    seed_default_roles(db_session)

    roles = {role.name: role for role in db_session.query(Role).all()}

    assert set(roles) == {
        "Administrator",
        "Clerk",
        "Member of Parliament",
        "Viewer",
    }
    for role_name, expected_permissions in DEFAULT_ROLE_PERMISSIONS.items():
        assert {permission.code for permission in roles[role_name].permissions} == set(
            expected_permissions
        )


def test_user_permission_is_inherited_from_assigned_role(db_session):
    permission = Permission(code="schedule_item", description="Schedule an item")
    clerk = Role(name="Clerk", permissions=[permission])
    user = make_user(db_session, "EMP-RBAC-001", [clerk])

    assert user.has_permission("schedule_item")
    assert not user.has_permission("manage_users")


def test_custom_role_and_permission_require_no_business_logic_change(db_session):
    permission = Permission(
        code="export_order_paper",
        description="Export an Order Paper",
    )
    custom_role = Role(name="Order Paper Publisher", permissions=[permission])
    user = make_user(db_session, "EMP-RBAC-002", [custom_role])
    db_session.commit()

    saved_user = db_session.get(User, user.id)

    assert saved_user.has_permission("export_order_paper")


def test_audit_api_checks_permission_instead_of_role_name(client, db_session):
    permission = Permission(code="view_audit", description="View audit logs")
    allowed_role = Role(name="Custom Auditor", permissions=[permission])
    denied_role = Role(name="Administrator", permissions=[])
    allowed_user = make_user(db_session, "EMP-RBAC-003", [allowed_role])
    denied_user = make_user(db_session, "EMP-RBAC-004", [denied_role])
    allowed_headers = auth_headers(db_session, allowed_user)
    denied_headers = auth_headers(db_session, denied_user)

    denied_response = client.get("/audit", headers=denied_headers)
    allowed_response = client.get("/audit", headers=allowed_headers)

    assert denied_response.status_code == 403
    assert allowed_response.status_code == 200
