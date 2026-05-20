from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ParliamentaryRecord, ParliamentarySession
from app.schemas.record import RecordDetailOut, RecordListOut

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[RecordListOut])
def list_records(
    session_id: UUID | None = Query(default=None),
    item_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ParliamentaryRecord]:
    query = select(ParliamentaryRecord).order_by(ParliamentaryRecord.created_at.desc())

    if session_id:
        query = query.where(ParliamentaryRecord.session_id == session_id)

    if item_type:
        query = query.where(ParliamentaryRecord.item_type == item_type)

    result = db.execute(query)
    return list(result.scalars().all())


@router.get("/{record_id}", response_model=RecordDetailOut)
def get_record(
    record_id: UUID,
    db: Session = Depends(get_db),
) -> ParliamentaryRecord:
    result = db.execute(
        select(ParliamentaryRecord)
        .join(ParliamentarySession)
        .where(ParliamentaryRecord.id == record_id)
    )
    record = result.scalars().first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return record
