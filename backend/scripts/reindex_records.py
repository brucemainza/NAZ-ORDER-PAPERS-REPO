"""Queue a resumable chunk-index backfill.

Usage:
    python -m scripts.reindex_records --batch-size 100 [--after RECORD_UUID]

The command only creates durable work. Run ``python -m app.jobs.worker`` to
process it; rerunning with the returned cursor safely resumes the backfill.
"""

import argparse
import json
from uuid import UUID

from app.ai.dependencies import get_embedding_provider
from app.ai.indexing.chunks import enqueue_chunk_backfill
from app.config import get_settings
from app.database import SessionLocal


def queue_backfill(*, batch_size: int, after_id: UUID | None) -> dict:
    settings = get_settings()
    provider = get_embedding_provider()
    with SessionLocal() as db:
        result = enqueue_chunk_backfill(
            db,
            model=provider.model_name,
            model_digest=provider.model_digest,
            preprocessing_version=settings.ai_preprocessing_version,
            after_id=after_id,
            limit=batch_size,
        )
        db.commit()
    return {
        "queued": result.queued,
        "next_cursor": str(result.next_cursor) if result.next_cursor else None,
        "complete": result.complete,
        "model": provider.model_name,
        "model_digest": provider.model_digest,
        "preprocessing_version": settings.ai_preprocessing_version,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue resumable chunk indexing")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--after", type=UUID, default=None)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 500:
        parser.error("--batch-size must be between 1 and 500")
    print(
        json.dumps(
            queue_backfill(batch_size=args.batch_size, after_id=args.after),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
