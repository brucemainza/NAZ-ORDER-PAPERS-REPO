from typing import Optional

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    employee_id: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employeeId: str
    name: str
    role: str
    status: str
    lastLogin: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut