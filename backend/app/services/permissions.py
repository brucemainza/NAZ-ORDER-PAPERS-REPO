from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role, User

PERMISSIONS = {
    "submit_question": "Submit questions for oral or written answer",
    "submit_motion": "Submit notices of motion",
    "review_submission": "Review submitted questions and motions",
    "approve_motion": "Approve a submission after review",
    "reject_submission": "Reject a submission after review",
    "request_changes": "Return a submission to its owner for changes",
    "schedule_item": "Schedule an approved item for a sitting",
    "view_reports": "View operational reports",
    "view_audit": "View the system audit trail",
    "manage_users": "Manage user accounts and account locks",
    "manage_roles": "Manage roles and permission assignments",
    "manage_sessions": "Manage parliamentary sessions",
    "search_archive": "Search archived parliamentary records",
    "view_archive": "View archived parliamentary records",
}

DEFAULT_ROLE_PERMISSIONS = {
    "Administrator": tuple(PERMISSIONS),
    "Clerk": (
        "review_submission",
        "approve_motion",
        "reject_submission",
        "request_changes",
        "schedule_item",
        "view_reports",
        "view_audit",
        "manage_sessions",
        "search_archive",
        "view_archive",
    ),
    "Member of Parliament": (
        "submit_question",
        "submit_motion",
        "search_archive",
        "view_archive",
    ),
    "Viewer": (
        "view_reports",
        "search_archive",
        "view_archive",
    ),
}

LEGACY_ROLE_NAMES = {
    "Admin": "Administrator",
    "Senior Clerk": "Clerk",
    "Clerk": "Clerk",
}


def seed_default_roles(db: Session) -> None:
    permissions = {
        permission.code: permission
        for permission in db.scalars(select(Permission)).all()
    }
    for code, description in PERMISSIONS.items():
        if code not in permissions:
            permissions[code] = Permission(code=code, description=description)
            db.add(permissions[code])
    db.flush()

    roles = {role.name: role for role in db.scalars(select(Role)).all()}
    for role_name, permission_codes in DEFAULT_ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if role is None:
            role = Role(name=role_name)
            roles[role_name] = role
            db.add(role)
        role.permissions = [permissions[code] for code in permission_codes]
    db.flush()


def assign_legacy_roles(db: Session) -> None:
    roles = {role.name: role for role in db.scalars(select(Role)).all()}
    for user in db.scalars(select(User)).all():
        if user.roles:
            continue
        mapped_name = LEGACY_ROLE_NAMES.get(user.role)
        if mapped_name and mapped_name in roles:
            user.roles.append(roles[mapped_name])
