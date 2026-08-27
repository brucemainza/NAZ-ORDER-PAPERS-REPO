from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord, ParliamentarySession


@dataclass(frozen=True, slots=True)
class SessionReportSession:
    id: UUID
    code: str
    name: str
    start_date: date
    end_date: date
    status: str


@dataclass(frozen=True, slots=True)
class SessionReportSummary:
    total: int
    questions: int
    motions: int


@dataclass(frozen=True, slots=True)
class SessionReportItem:
    id: UUID
    item_type: str
    member: str
    ministry: str | None
    subject: str
    full_text: str
    status: str
    sitting_date: date | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SessionReport:
    session: SessionReportSession
    summary: SessionReportSummary
    items: list[SessionReportItem]


class SessionReportReader(ABC):
    @abstractmethod
    def read(self, session_id: UUID) -> SessionReport | None:
        """Return format-neutral report data for one session."""


class DatabaseSessionReportReader(SessionReportReader):
    def __init__(self, db: Session) -> None:
        self._db = db

    def read(self, session_id: UUID) -> SessionReport | None:
        session = self._db.get(ParliamentarySession, session_id)
        if session is None:
            return None

        records = list(
            self._db.scalars(
                select(ParliamentaryRecord)
                .where(ParliamentaryRecord.session_id == session.id)
                .order_by(
                    ParliamentaryRecord.created_at.asc(),
                    ParliamentaryRecord.id.asc(),
                )
            ).all()
        )
        items = [
            SessionReportItem(
                id=record.id,
                item_type=record.item_type,
                member=record.member,
                ministry=record.ministry,
                subject=record.subject,
                full_text=record.full_text,
                status=record.status,
                sitting_date=record.sitting_date,
                created_at=record.created_at,
            )
            for record in records
        ]
        return SessionReport(
            session=SessionReportSession(
                id=session.id,
                code=session.code,
                name=session.name,
                start_date=session.start_date,
                end_date=session.end_date,
                status=session.status,
            ),
            summary=SessionReportSummary(
                total=len(items),
                questions=sum(
                    item.item_type == "Question" for item in items
                ),
                motions=sum(item.item_type == "Motion" for item in items),
            ),
            items=items,
        )
