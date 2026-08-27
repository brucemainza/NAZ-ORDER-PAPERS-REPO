"""Shared handling for database conflicts at API transaction boundaries."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DatabaseConflict(RuntimeError):
    pass


def flush_transaction(db: Session, *, conflict_message: str) -> None:
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise DatabaseConflict(conflict_message) from error


def commit_transaction(db: Session, *, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise DatabaseConflict(conflict_message) from error
    except Exception:
        db.rollback()
        raise
