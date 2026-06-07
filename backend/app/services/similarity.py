from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import ParliamentaryRecord
from app.retrieval.bm25 import RankedMatch, rank_records


def find_previously_addressed_candidates(
    db: Session,
    *,
    record: ParliamentaryRecord,
    limit: int = 5,
) -> list[RankedMatch]:
    historical_records = list(
        db.execute(
            select(ParliamentaryRecord)
            .where(ParliamentaryRecord.id != record.id)
            .order_by(ParliamentaryRecord.created_at.desc())
        ).scalars().all()
    )
    query_text = " ".join([record.subject, record.full_text, record.member, record.ministry or ""])
    bm25_matches = rank_records(query_text, historical_records, limit)

    vector_matches = _vector_matches(db, record.id, limit)
    by_record_id: dict[UUID, RankedMatch] = {match.record.id: match for match in bm25_matches}

    for vector_match in vector_matches:
        existing = by_record_id.get(vector_match.record.id)
        if existing:
            existing.score = round(max(existing.score, vector_match.score), 2)
            existing.matched_terms = sorted(set(existing.matched_terms + vector_match.matched_terms))
        else:
            by_record_id[vector_match.record.id] = vector_match

    return sorted(by_record_id.values(), key=lambda match: match.score, reverse=True)[:limit]


def _vector_matches(db: Session, record_id: UUID, limit: int) -> list[RankedMatch]:
    try:
        rows = db.execute(
            text(
                """
                SELECT candidate.id, 100 - ((source.embedding <=> candidate.embedding) * 100) AS score
                FROM parliamentary_records source
                JOIN parliamentary_records candidate
                  ON candidate.id != source.id
                 AND candidate.embedding IS NOT NULL
                WHERE source.id = :record_id
                  AND source.embedding IS NOT NULL
                ORDER BY source.embedding <=> candidate.embedding
                LIMIT :limit
                """
            ),
            {"record_id": record_id, "limit": limit},
        ).all()
    except Exception:
        db.rollback()
        return []

    if not rows:
        return []

    records = {
        item.id: item
        for item in db.execute(
            select(ParliamentaryRecord).where(ParliamentaryRecord.id.in_([row.id for row in rows]))
        ).scalars().all()
    }
    return [
        RankedMatch(
            record=records[row.id],
            score=round(max(0, min(100, float(row.score or 0))), 2),
            matched_terms=["pgvector"],
        )
        for row in rows
        if row.id in records
    ]
