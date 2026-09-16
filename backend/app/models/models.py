from datetime import date, datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect as sqlalchemy_inspect,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSONB,
    TSVECTOR,
    UUID as PostgresUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.database import Base


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

related_item_links = Table(
    "related_item_links",
    Base.metadata,
    Column(
        "record_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("parliamentary_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "related_record_id",
        PostgresUUID(as_uuid=True),
        ForeignKey("parliamentary_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    CheckConstraint(
        "record_id <> related_record_id",
        name="related_item_links_distinct_records",
    ),
)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    code: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str] = mapped_column(Text)

    roles: Mapped[List["Role"]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[List["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    employee_id: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user")
    roles: Mapped[List[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    @property
    def permission_codes(self) -> list[str]:
        return sorted(
            {
                permission.code
                for assigned_role in self.roles
                for permission in assigned_role.permissions
            }
        )

    @property
    def role_names(self) -> list[str]:
        return sorted(assigned_role.name for assigned_role in self.roles)

    @property
    def primary_role_name(self) -> str:
        return self.role_names[0] if self.roles else self.role

    def has_permission(self, permission_code: str) -> bool:
        return permission_code in self.permission_codes


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    jti: Mapped[str] = mapped_column(Text, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[Optional[str]] = mapped_column(Text)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    
    user: Mapped["User"] = relationship(back_populates="sessions")


class ParliamentarySession(Base):
    __tablename__ = "parliamentary_sessions"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[List["ParliamentaryRecord"]] = relationship(back_populates="session")


class ParliamentaryRecord(Base):
    __tablename__ = "parliamentary_records"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft', 'Submitted', 'Under Review', 'Approved', "
            "'Rejected', 'Scheduled', 'Answered', 'Discussed', 'Archived')",
            name="parliamentary_records_status_check",
        ),
        Index(
            "idx_parliamentary_records_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    item_type: Mapped[str] = mapped_column(Text)
    session_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_sessions.id"))
    member: Mapped[str] = mapped_column(Text)
    ministry: Mapped[Optional[str]] = mapped_column(Text)
    answer_type: Mapped[Optional[str]] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    full_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    submitted_by: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    sitting_date: Mapped[Optional[date]] = mapped_column(Date)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))
    embedding_model: Mapped[Optional[str]] = mapped_column(Text)
    normalized_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    search_vector = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(subject, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(full_text, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(member, '')), 'C') || "
            "setweight(to_tsvector('english', coalesce(ministry, '')), 'C')",
            persisted=True,
        ),
    )

    session: Mapped["ParliamentarySession"] = relationship(back_populates="records")
    submitter: Mapped[Optional["User"]] = relationship()
    related_items: Mapped[List["ParliamentaryRecord"]] = relationship(
        "ParliamentaryRecord",
        secondary=related_item_links,
        primaryjoin=id == related_item_links.c.record_id,
        secondaryjoin=id == related_item_links.c.related_record_id,
        back_populates="referenced_by_items",
        order_by="ParliamentaryRecord.created_at",
    )
    referenced_by_items: Mapped[List["ParliamentaryRecord"]] = relationship(
        "ParliamentaryRecord",
        secondary=related_item_links,
        primaryjoin=id == related_item_links.c.related_record_id,
        secondaryjoin=id == related_item_links.c.record_id,
        back_populates="related_items",
        order_by="ParliamentaryRecord.created_at",
    )
    response: Mapped[Optional["QuestionResponse"]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        uselist=False,
    )


class QuestionResponse(Base):
    __tablename__ = "question_responses"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("parliamentary_records.id", ondelete="CASCADE"),
        unique=True,
    )
    response_text: Mapped[str] = mapped_column(Text)
    response_date: Mapped[date] = mapped_column(Date)
    recorded_by: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    record: Mapped["ParliamentaryRecord"] = relationship(
        back_populates="response",
    )
    recorder: Mapped["User"] = relationship()


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text)
    session_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_sessions.id"), nullable=True)
    top_result_ids: Mapped[Optional[List[UUID]]] = mapped_column(ARRAY(PostgresUUID(as_uuid=True)), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    __table_args__ = (
        CheckConstraint(
            "(decision = 'Clear (New)' AND similar_record_id IS NULL "
            "AND is_duplicate = false) OR "
            "(decision IN ('Duplicate', 'Substantially Similar') "
            "AND similar_record_id IS NOT NULL AND is_duplicate = true)",
            name="review_decisions_relationship_check",
        ),
        CheckConstraint(
            "similar_record_id IS NULL OR record_id <> similar_record_id",
            name="review_decisions_distinct_records",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    record_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_records.id"))
    similar_record_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("parliamentary_records.id"), nullable=True)
    decision: Mapped[str] = mapped_column(Text)
    is_duplicate: Mapped[bool] = mapped_column(default=False)
    reviewer_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    record: Mapped["ParliamentaryRecord"] = relationship(foreign_keys=[record_id])
    similar_record: Mapped[Optional["ParliamentaryRecord"]] = relationship(foreign_keys=[similar_record_id])
    reviewer: Mapped["User"] = relationship()


class WorkflowDecision(Base):
    __tablename__ = "workflow_decisions"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("parliamentary_records.id"),
    )
    action: Mapped[str] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewer_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    record: Mapped["ParliamentaryRecord"] = relationship()
    reviewer: Mapped["User"] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[Optional[str]] = mapped_column(Text)
    entity_id: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship()


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'retry', 'completed', 'dead_letter')",
            name="background_jobs_status_check",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_type: Mapped[str] = mapped_column(Text, index=True)
    deduplication_key: Mapped[str] = mapped_column(Text, unique=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    lock_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[Optional[str]] = mapped_column(Text)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    aggregate_type: Mapped[str] = mapped_column(Text)
    aggregate_id: Mapped[str] = mapped_column(Text, index=True)
    event_type: Mapped[str] = mapped_column(Text, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(Text, default="pending", server_default="pending")
    job_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("background_jobs.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(
        Text,
        default="running",
        server_default="running",
    )
    details: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )


class RecordChunk(Base):
    __tablename__ = "record_chunks"
    __table_args__ = (
        UniqueConstraint(
            "record_id",
            "chunk_index",
            "content_hash",
            "embedding_model",
            "model_digest",
            "preprocessing_version",
            name="uq_record_chunks_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("parliamentary_records.id", ondelete="CASCADE"),
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(768))
    embedding_model: Mapped[str] = mapped_column(Text)
    model_digest: Mapped[str] = mapped_column(Text)
    dimension: Mapped[int] = mapped_column(Integer)
    preprocessing_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    scope: Mapped[str] = mapped_column(Text)
    key: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[str] = mapped_column(String(64))
    response_status: Mapped[Optional[int]] = mapped_column(Integer)
    response_body: Mapped[Optional[dict]] = mapped_column(JSONB)
    resource_type: Mapped[Optional[str]] = mapped_column(Text)
    resource_id: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


@event.listens_for(ParliamentaryRecord, "before_insert")
def set_record_identity_before_insert(_mapper, _connection, record) -> None:
    from app.similarity.normalization import record_content_hash

    record.normalized_hash = record_content_hash(
        record.item_type,
        record.subject,
        record.full_text,
    )
    record.version = record.version or 1


@event.listens_for(ParliamentaryRecord, "before_update")
def update_record_identity_before_update(_mapper, _connection, record) -> None:
    state = sqlalchemy_inspect(record)
    content_changed = any(
        state.attrs[field].history.has_changes()
        for field in ("item_type", "subject", "full_text")
    )
    if not content_changed:
        return
    from app.similarity.normalization import record_content_hash

    record.normalized_hash = record_content_hash(
        record.item_type,
        record.subject,
        record.full_text,
    )
    record.version = (record.version or 1) + 1
