import os
from collections.abc import Mapping
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

SECRET_KEY = os.getenv("JWT_SECRET", "naz-order-papers-jwt-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
TokenPayload = dict[str, Any]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def create_access_token(data: Mapping[str, Any]) -> tuple[str, str]:
    jti = str(uuid4())
    to_encode: TokenPayload = dict(data)
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "iat": datetime.now(timezone.utc),
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti


def verify_access_token(token: str) -> TokenPayload | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload if isinstance(payload, dict) else None
    except jwt.PyJWTError:
        return None
