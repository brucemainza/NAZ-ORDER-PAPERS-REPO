from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ParliamentarySession
from app.schemas.session import SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)) -> list[ParliamentarySession]:
    result = db.execute(
        select(ParliamentarySession).order_by(ParliamentarySession.start_date.desc())
    )
    return list(result.scalars().all())
