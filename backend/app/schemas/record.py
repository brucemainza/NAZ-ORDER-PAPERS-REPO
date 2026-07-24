from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecordListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    session_id: UUID
    member: str
    ministry: str | None
    answer_type: str | None
    subject: str
    status: str
    submitted_by: UUID | None
    sitting_date: date | None
    created_at: datetime
    session_name: str | None = None

    @classmethod
    def from_orm(cls, obj):
        data = {
            'id': obj.id,
            'item_type': obj.item_type,
            'session_id': obj.session_id,
            'member': obj.member,
            'ministry': obj.ministry,
            'answer_type': obj.answer_type,
            'subject': obj.subject,
            'status': obj.status,
            'submitted_by': obj.submitted_by,
            'sitting_date': obj.sitting_date,
            'created_at': obj.created_at,
            'session_name': obj.session.name if obj.session else None,
        }
        return cls(**data)


class RecordDetailOut(RecordListOut):
    full_text: str
