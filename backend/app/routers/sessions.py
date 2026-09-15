from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import add_audit_log, request_ip, require_permission
from app.models import ParliamentarySession, User
from app.schemas.session import SessionOut, SessionUpdate
from app.services.transactions import DatabaseConflict, commit_transaction

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)) -> list[ParliamentarySession]:
    result = db.execute(
        select(ParliamentarySession).order_by(ParliamentarySession.start_date.desc())
    )
    return list(result.scalars().all())


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_sessions")),
) -> ParliamentarySession:
    session = db.get(ParliamentarySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(session, field, value)

    add_audit_log(
        db,
        user_id=user.id,
        action="session_update",
        entity_type="parliamentary_session",
        entity_id=str(session.id),
        details=",".join(sorted(updates)) or None,
        ip_address=request_ip(request),
    )
    try:
        commit_transaction(
            db,
            conflict_message="The session conflicts with another committed change",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    db.refresh(session)
    return session


@router.delete("/{session_id}")
def delete_session(
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_sessions")),
) -> dict[str, bool]:
    session = db.get(ParliamentarySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_name = session.name
    db.delete(session)
    add_audit_log(
        db,
        user_id=user.id,
        action="session_delete",
        entity_type="parliamentary_session",
        entity_id=str(session_id),
        details=session_name,
        ip_address=request_ip(request),
    )
    try:
        commit_transaction(
            db,
            conflict_message="This session has linked records and cannot be deleted",
        )
    except DatabaseConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"success": True}
