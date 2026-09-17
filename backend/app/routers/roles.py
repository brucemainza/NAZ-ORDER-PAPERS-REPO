from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_permission
from app.models import Role, User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[str])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("manage_users")),
) -> list[str]:
    result = db.execute(select(Role.name).order_by(Role.name))
    return list(result.scalars().all())
