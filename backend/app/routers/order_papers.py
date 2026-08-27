from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ParliamentaryRecord, User
from app.schemas.order_paper import OrderPaperOut, OrderPaperSection
from app.services.submission_status import SubmissionStatus

router = APIRouter(prefix="/order-papers", tags=["order-papers"])


@router.get("/{sitting_date}", response_model=OrderPaperOut)
def generate_order_paper(
    sitting_date: date,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> OrderPaperOut:
    records = db.scalars(
        select(ParliamentaryRecord)
        .where(
            ParliamentaryRecord.status == SubmissionStatus.SCHEDULED.value,
            ParliamentaryRecord.sitting_date == sitting_date,
        )
        .order_by(
            ParliamentaryRecord.created_at.asc(),
            ParliamentaryRecord.id.asc(),
        )
    ).all()

    questions = [record for record in records if record.item_type == "Question"]
    motions = [record for record in records if record.item_type == "Motion"]
    sections = [
        OrderPaperSection(
            heading="QUESTIONS",
            item_type="Question",
            items=questions,
        ),
        OrderPaperSection(
            heading="NOTICES OF MOTION",
            item_type="Motion",
            items=motions,
        ),
    ]
    return OrderPaperOut(
        title="NATIONAL ASSEMBLY OF ZAMBIA ORDER PAPER",
        sitting_date=sitting_date,
        total_items=len(records),
        sections=sections,
    )
