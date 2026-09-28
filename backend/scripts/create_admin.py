"""Create the first Administrator account on a fresh database.

Usage:
    ADMIN_PASSWORD=... python -m scripts.create_admin --employee-id ADMIN-001

The password is read from the ADMIN_PASSWORD environment variable so it never
appears in the process list. An existing account is left untouched unless
--reset-password is given, so the command is safe to rerun on every deploy.
"""

import argparse
import json
from os import getenv

from sqlalchemy import select

from app.database import SessionLocal
from app.lib.auth import get_password_hash
from app.models import Role, User
from app.services.permissions import seed_default_roles

ADMIN_ROLE = "Administrator"


def ensure_admin(
    *,
    employee_id: str,
    name: str,
    password: str,
    reset_password: bool,
) -> dict:
    with SessionLocal() as db:
        seed_default_roles(db)
        role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE))
        if role is None:
            raise RuntimeError(f"role {ADMIN_ROLE!r} was not seeded")

        user = db.scalar(select(User).where(User.employee_id == employee_id))
        if user is None:
            user = User(
                employee_id=employee_id,
                name=name,
                role="Admin",
                status="Active",
                password_hash=get_password_hash(password),
            )
            db.add(user)
            action = "created"
        elif reset_password:
            user.password_hash = get_password_hash(password)
            user.status = "Active"
            user.failed_login_attempts = 0
            user.locked_at = None
            action = "password_reset"
        else:
            action = "exists"

        if role not in user.roles:
            user.roles.append(role)
        db.commit()
    return {"employee_id": employee_id, "action": action}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first Administrator")
    parser.add_argument("--employee-id", default="ADMIN-001")
    parser.add_argument("--name", default="System Administrator")
    parser.add_argument("--reset-password", action="store_true")
    args = parser.parse_args()

    password = getenv("ADMIN_PASSWORD", "")
    if len(password) < 8:
        parser.error("ADMIN_PASSWORD must be set and at least 8 characters")

    print(
        json.dumps(
            ensure_admin(
                employee_id=args.employee_id.strip(),
                name=args.name.strip(),
                password=password,
                reset_password=args.reset_password,
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
