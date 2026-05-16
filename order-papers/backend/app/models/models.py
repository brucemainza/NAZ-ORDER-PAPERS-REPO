from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    employee_id: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ParliamentarySession(Base):
    __tablename__ = "parliamentary_sessions"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[List["ParliamentaryRecord"]] = relationship(back_populates="session")


class ParliamentaryRecord(Base):
    __tablename__ = "parliamentary_records"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True)
    item_type: Mapped[str] = mapped_column(Text)
    session_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_sessions.id"))
    member: Mapped[str] = mapped_column(Text)
    ministry: Mapped[Optional[str]] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[ParliamentarySession] = relationship(back_populates="records")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    query_text: Mapped[str] = mapped_column(Text)
    session_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_sessions.id"))
    top_result_ids: Mapped[Optional[List[UUID]]] = mapped_column(ARRAY(PostgresUUID(as_uuid=True)))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
