from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: UUID
    user_id: UUID | None
    user_name: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: str | None
    ip_address: str | None
    created_at: datetime
