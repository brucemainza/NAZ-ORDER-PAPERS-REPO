from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.interfaces import EmbeddingProvider
from app.jobs.queue import enqueue_outbox_job
from app.models import ParliamentaryRecord, RecordChunk


def chunk_record(
    subject: str,
    full_text: str,
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    if max_chars < 80:
        raise ValueError("max_chars must be at least 80")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    clean_subject = " ".join(subject.split())
    prefix = f"Subject: {clean_subject}\n\n"
    if len(prefix) >= max_chars:
        prefix = f"Subject: {clean_subject[: max_chars - 12].rstrip()}\n\n"
    body_limit = max_chars - len(prefix)
    words = " ".join(full_text.split()).split()
    if not words:
        return [prefix.rstrip()]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        used = 0
        while end < len(words):
            addition = len(words[end]) + (1 if end > start else 0)
            if end > start and used + addition > body_limit:
                break
            used += addition
            end += 1
        if end == start:
            end += 1
        chunks.append(prefix + " ".join(words[start:end]))
        if end >= len(words):
            break

        overlap_start = end
        overlap_used = 0
        while overlap_start > start + 1:
            candidate = len(words[overlap_start - 1]) + (1 if overlap_used else 0)
            if overlap_used + candidate > overlap_chars:
                break
            overlap_start -= 1
            overlap_used += candidate
        start = overlap_start
    return chunks


class ChunkIndexingService:
    def __init__(
        self,
        db: Session,
        provider: EmbeddingProvider,
        *,
        max_chars: int,
        overlap_chars: int,
        preprocessing_version: str,
    ) -> None:
        self._db = db
        self._provider = provider
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars
        self._preprocessing_version = preprocessing_version

    def index_record(self, record: ParliamentaryRecord) -> int:
        texts = chunk_record(
            record.subject,
            record.full_text,
            max_chars=self._max_chars,
            overlap_chars=self._overlap_chars,
        )
        digest = self._provider.model_digest
        desired = [
            (index, sha256(text.encode("utf-8")).hexdigest(), text)
            for index, text in enumerate(texts)
        ]
        existing = list(
            self._db.scalars(
                select(RecordChunk).where(
                    RecordChunk.record_id == record.id,
                    RecordChunk.embedding_model == self._provider.model_name,
                    RecordChunk.model_digest == digest,
                    RecordChunk.dimension == self._provider.dimension,
                    RecordChunk.preprocessing_version == self._preprocessing_version,
                )
            ).all()
        )
        existing_keys = {(chunk.chunk_index, chunk.content_hash) for chunk in existing}
        desired_keys = {(index, content_hash) for index, content_hash, _ in desired}
        for stale in existing:
            if (stale.chunk_index, stale.content_hash) not in desired_keys:
                self._db.delete(stale)

        missing = [item for item in desired if (item[0], item[1]) not in existing_keys]
        if not missing:
            return 0
        vectors = self._provider.embed_documents([item[2] for item in missing])
        if len(vectors) != len(missing):
            raise RuntimeError("embedding batch result count mismatch")
        for (index, content_hash, text), vector in zip(missing, vectors, strict=True):
            if len(vector) != self._provider.dimension:
                raise RuntimeError(
                    "embedding dimension mismatch: "
                    f"expected {self._provider.dimension}, got {len(vector)}"
                )
            self._db.add(
                RecordChunk(
                    record_id=record.id,
                    chunk_index=index,
                    chunk_text=text,
                    content_hash=content_hash,
                    embedding=vector,
                    embedding_model=self._provider.model_name,
                    model_digest=digest,
                    dimension=self._provider.dimension,
                    preprocessing_version=self._preprocessing_version,
                )
            )
        self._db.flush()
        return len(missing)


@dataclass(frozen=True)
class BackfillResult:
    queued: int
    next_cursor: UUID | None
    complete: bool


@dataclass(frozen=True)
class IndexCoverage:
    eligible_records: int
    indexed_records: int
    coverage_percent: float


def chunk_index_coverage(
    db: Session,
    *,
    model: str,
    model_digest: str,
    dimension: int,
    preprocessing_version: str,
) -> IndexCoverage:
    eligible = db.scalar(
        select(func.count(ParliamentaryRecord.id)).where(
            ParliamentaryRecord.status != "Draft"
        )
    ) or 0
    indexed = db.scalar(
        select(func.count(func.distinct(RecordChunk.record_id)))
        .join(
            ParliamentaryRecord,
            ParliamentaryRecord.id == RecordChunk.record_id,
        )
        .where(
            ParliamentaryRecord.status != "Draft",
            RecordChunk.embedding.is_not(None),
            RecordChunk.embedding_model == model,
            RecordChunk.model_digest == model_digest,
            RecordChunk.dimension == dimension,
            RecordChunk.preprocessing_version == preprocessing_version,
        )
    ) or 0
    percent = 100.0 if eligible == 0 else round((indexed / eligible) * 100, 2)
    return IndexCoverage(
        eligible_records=int(eligible),
        indexed_records=int(indexed),
        coverage_percent=percent,
    )


def enqueue_chunk_backfill(
    db: Session,
    *,
    model: str,
    model_digest: str,
    preprocessing_version: str,
    after_id: UUID | None = None,
    limit: int = 100,
) -> BackfillResult:
    query = select(ParliamentaryRecord).order_by(ParliamentaryRecord.id).limit(limit)
    if after_id is not None:
        query = query.where(ParliamentaryRecord.id > after_id)
    records = list(db.scalars(query).all())
    for record in records:
        enqueue_outbox_job(
            db,
            job_type="index_record_chunks",
            payload={
                "record_id": str(record.id),
                "record_version": record.version,
                "model": model,
                "model_digest": model_digest,
                "preprocessing_version": preprocessing_version,
            },
            deduplication_key=(
                f"index_record_chunks:{record.id}:{record.version}:"
                f"{model_digest}:{preprocessing_version}"
            ),
            aggregate_type="parliamentary_record",
            aggregate_id=str(record.id),
            event_type="record.chunk_indexing_requested",
        )
    return BackfillResult(
        queued=len(records),
        next_cursor=records[-1].id if records else after_id,
        complete=len(records) < limit,
    )
