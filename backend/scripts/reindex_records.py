"""Batch re-index all parliamentary records with the configured embedding model.

Usage:
    python -m scripts.reindex_records [--batch-size 8]

This script should be run after changing the embedding model or vector dimension.
It calls the local Ollama instance defined by OLLAMA_BASE_URL.
"""

import argparse
import logging
import sys
from pathlib import Path

# Allow imports from the backend app package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.ai.dependencies import get_embedding_provider
from app.ai.normalization import build_similarity_text
from app.config import get_settings
from app.database import SessionLocal
from app.models import ParliamentaryRecord

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def reindex(batch_size: int) -> None:
    settings = get_settings()
    provider = get_embedding_provider()

    logger.info("Starting batch re-index with model: %s", provider.model_name)
    logger.info("Expected embedding dimension: %d", provider.dimension)

    with SessionLocal() as db:
        records = list(
            db.execute(
                select(ParliamentaryRecord).where(
                    ParliamentaryRecord.status != "Draft"
                )
            ).scalars().all()
        )

        total = len(records)
        logger.info("Found %d non-draft records to index", total)

        for start in range(0, total, batch_size):
            batch = records[start : start + batch_size]
            texts = [
                build_similarity_text(record.subject, record.full_text)
                for record in batch
            ]

            try:
                embeddings = provider.embed_documents(texts)
            except Exception as exc:
                logger.error("Failed to embed batch %d-%d: %s", start + 1, start + len(batch), exc)
                continue

            for record, embedding in zip(batch, embeddings):
                record.embedding = embedding
                record.embedding_model = provider.model_name

            db.commit()
            logger.info(
                "Indexed records %d-%d of %d",
                start + 1,
                min(start + batch_size, total),
                total,
            )

    logger.info("Batch re-index complete")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-index parliamentary record embeddings using the configured local model."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Number of records to embed in each Ollama request (default: 8).",
    )
    args = parser.parse_args()

    reindex(args.batch_size)


if __name__ == "__main__":
    main()
