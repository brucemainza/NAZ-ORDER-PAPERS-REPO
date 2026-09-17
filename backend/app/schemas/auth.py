from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    employee_id: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: str
    name: str
    role: str
    roles: list[str]
    permissions: list[str]
    status: str
    lastLogin: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut
