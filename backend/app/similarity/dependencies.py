from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.similarity.base import SimilarityBackend
from app.similarity.duplicate_detection import (
    DuplicateChecker,
    DuplicateDetectionService,
)
from app.similarity.embeddings import EmbeddingGenerator, TokenHashEmbeddingGenerator
from app.similarity.pgvector_backend import PgVectorSimilarityBackend
from app.similarity.presentation import (
    DatabaseSimilarityResultFormatter,
    SimilarityResultFormatter,
)


def get_embedding_generator() -> EmbeddingGenerator:
    return TokenHashEmbeddingGenerator(dimension=384)


def get_similarity_backend(
    db: Session = Depends(get_db),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
) -> SimilarityBackend:
    return PgVectorSimilarityBackend(db, embedding_generator)


def get_duplicate_checker(
    db: Session = Depends(get_db),
    similarity_backend: SimilarityBackend = Depends(get_similarity_backend),
) -> DuplicateChecker:
    return DuplicateDetectionService(db, similarity_backend)


def get_similarity_result_formatter(
    db: Session = Depends(get_db),
) -> SimilarityResultFormatter:
    return DatabaseSimilarityResultFormatter(db)
