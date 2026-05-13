from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecordListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    session_id: UUID
    member: str
    ministry: str | None
    subject: str
    status: str
    created_at: datetime


class RecordDetailOut(RecordListOut):
    full_text: str
