from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import add_audit_log, get_current_user, request_ip
from app.models import ParliamentaryRecord, ParliamentarySession, User
from app.schemas.record import RecordDetailOut, RecordListOut
from app.schemas.search import SearchResultOut
from app.services.similarity import find_previously_addressed_candidates

router = APIRouter(prefix="/records", tags=["records"])


@router.get("", response_model=list[RecordListOut])
def list_records(
    session_id: UUID | None = Query(default=None),
    item_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    query_text: str | None = Query(default=None, alias="query_text"),
    limit: int = Query(default=15, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RecordListOut]:
    query = select(ParliamentaryRecord).options(joinedload(ParliamentaryRecord.session)).order_by(ParliamentaryRecord.created_at.desc())

    if session_id:
        query = query.where(ParliamentaryRecord.session_id == session_id)

    if item_type:
        normalized_item_type = item_type.strip().lower()
        item_type_lookup = {
            "question": "question",
            "motion": "motion",
        }
        query = query.where(func.lower(ParliamentaryRecord.item_type) == item_type_lookup.get(normalized_item_type, normalized_item_type))

    if status:
        normalized_status = status.strip().lower()
        status_lookup = {
            "pending": "under review",
            "pending review": "under review",
            "under review": "under review",
            "duplicate": "duplicate",
            "historical": "historical",
            "clear": "clear (new)",
            "clear (new)": "clear (new)",
            "reviewed": "reviewed",
        }
        query = query.where(func.lower(ParliamentaryRecord.status) == status_lookup.get(normalized_status, normalized_status))

    if query_text:
        search_term = f"%{query_text.strip()}%"
        query = query.where(
            or_(
                ParliamentaryRecord.subject.ilike(search_term),
                ParliamentaryRecord.member.ilike(search_term),
                ParliamentaryRecord.ministry.ilike(search_term),
                ParliamentaryRecord.full_text.ilike(search_term),
            )
        )

    query = query.offset(offset).limit(limit)
    result = db.execute(query)
    records = list(result.scalars().unique().all())
    return [RecordListOut.from_orm(record) for record in records]


@router.get("/{record_id}", response_model=RecordDetailOut)
def get_record(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParliamentaryRecord:
    result = db.execute(
        select(ParliamentaryRecord)
        .join(ParliamentarySession)
        .where(ParliamentaryRecord.id == record_id)
    )
    record = result.scalars().first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    add_audit_log(
        db,
        user_id=user.id,
        action="record_retrieval",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details=record.subject,
        ip_address=request_ip(request),
    )
    db.commit()

    return record


@router.get("/{record_id}/similar", response_model=list[SearchResultOut])
def similar_records(
    record_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SearchResultOut]:
    record = db.execute(select(ParliamentaryRecord).where(ParliamentaryRecord.id == record_id)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    candidates = find_previously_addressed_candidates(db, record=record, limit=5)
    add_audit_log(
        db,
        user_id=user.id,
        action="record_similarity",
        entity_type="parliamentary_record",
        entity_id=str(record.id),
        details="Fetched similar historical records",
        ip_address=request_ip(request),
    )
    db.commit()

    return [
        SearchResultOut(
            rank=index + 1,
            score=match.score,
            matched_terms=match.matched_terms,
            record=match.record,
        )
        for index, match in enumerate(candidates)
    ]
