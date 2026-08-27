from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.dependencies import get_embedding_provider
from app.ai.interfaces import EmbeddingProvider
from app.database import get_db
from app.similarity.base import SimilarityBackend
from app.similarity.duplicate_detection import (
    DuplicateChecker,
    DuplicateDetectionService,
)
from app.similarity.embeddings import EmbeddingGenerator
from app.similarity.pgvector_backend import PgVectorSimilarityBackend
from app.similarity.presentation import (
    DatabaseSimilarityResultFormatter,
    SimilarityResultFormatter,
)
from app.similarity.previously_addressed import (
    PreviouslyAddressedChecker,
    PreviouslyAddressedService,
)
from app.similarity.related_items import (
    RelatedItemLinker,
    RelatedItemLinkService,
)


def get_embedding_generator() -> EmbeddingGenerator:
    """Return the configured embedding provider as an EmbeddingGenerator."""
    return _EmbeddingGeneratorAdapter(get_embedding_provider())


def get_similarity_backend(
    db: Session = Depends(get_db),
    embedding_generator: EmbeddingGenerator = Depends(get_embedding_generator),
) -> SimilarityBackend:
    return PgVectorSimilarityBackend(db, embedding_generator)


class _EmbeddingGeneratorAdapter(EmbeddingGenerator):
    """Thin adapter so the new Ollama provider satisfies the old ABC."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider

    @property
    def dimension(self) -> int:
        return self._provider.dimension

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def embed(self, text: str) -> list[float]:
        return self._provider.embed_query(text)


def get_duplicate_checker(
    db: Session = Depends(get_db),
    similarity_backend: SimilarityBackend = Depends(get_similarity_backend),
) -> DuplicateChecker:
    return DuplicateDetectionService(db, similarity_backend)


def get_similarity_result_formatter(
    db: Session = Depends(get_db),
) -> SimilarityResultFormatter:
    return DatabaseSimilarityResultFormatter(db)


def get_previously_addressed_checker(
    db: Session = Depends(get_db),
    similarity_backend: SimilarityBackend = Depends(get_similarity_backend),
) -> PreviouslyAddressedChecker:
    return PreviouslyAddressedService(db, similarity_backend)


def get_related_item_linker(
    db: Session = Depends(get_db),
) -> RelatedItemLinker:
    return RelatedItemLinkService(db)
