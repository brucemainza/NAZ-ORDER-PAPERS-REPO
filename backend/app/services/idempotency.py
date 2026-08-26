"""Transactional idempotency support for domain write endpoints."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import IdempotencyKey


class IdempotencyConflict(ValueError):
    """Raised when one key is reused for a different request payload."""


class IdempotencyInProgress(RuntimeError):
    """Raised for a committed key that has no reusable result."""


def _request_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def claim_idempotency_key(
    db: Session,
    *,
    scope: str,
    key: str | None,
    payload: dict[str, Any],
    user_id: UUID,
) -> IdempotencyKey | None:
    """Serialize a key claim and create it inside the caller's transaction."""

    if key is None:
        return None

    request_hash = _request_hash(payload)
    lock_digest = sha256(f"{scope}\0{key}".encode("utf-8")).digest()
    advisory_lock_id = int.from_bytes(lock_digest[:8], "big", signed=True)
    db.execute(select(func.pg_advisory_xact_lock(advisory_lock_id)))

    existing = db.scalar(
        select(IdempotencyKey)
        .where(IdempotencyKey.scope == scope, IdempotencyKey.key == key)
        .with_for_update()
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise IdempotencyConflict(
                "Idempotency-Key was already used with a different payload"
            )
        if existing.response_body is None:
            raise IdempotencyInProgress(
                "The operation for this Idempotency-Key has no reusable result"
            )
        return existing

    entry = IdempotencyKey(
        scope=scope,
        key=key,
        request_hash=request_hash,
        user_id=user_id,
    )
    db.add(entry)
    db.flush()
    return entry


def cached_idempotency_response(entry: IdempotencyKey | None) -> dict | None:
    if entry is None or entry.response_body is None:
        return None
    return entry.response_body


def complete_idempotency_key(
    entry: IdempotencyKey | None,
    *,
    response_status: int,
    response_body: dict,
    resource_type: str,
    resource_id: str,
) -> None:
    if entry is None:
        return
    entry.response_status = response_status
    entry.response_body = response_body
    entry.resource_type = resource_type
    entry.resource_id = resource_id
