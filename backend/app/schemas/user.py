from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

UserStatus = Literal["Active", "Inactive"]


class UserSummaryOut(BaseModel):
    id: UUID
    employee_id: str
    name: str
    role: str
    status: str
    last_login_at: datetime | None = None


class UserCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1)
    role_name: str = Field(min_length=1)
    status: UserStatus = "Active"


class UserCreateResponse(BaseModel):
    user: UserSummaryOut
    temporary_password: str


class UserRoleUpdate(BaseModel):
    role_name: str = Field(min_length=1)


class PasswordResetResponse(BaseModel):
    temporary_password: str
