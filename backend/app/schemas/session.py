from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    start_date: date
    end_date: date
    status: str
