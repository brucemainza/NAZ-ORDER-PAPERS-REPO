"""Swappable embedding and similarity-search contracts."""

from app.similarity.base import SimilarityBackend, SimilarityMatch
from app.similarity.embeddings import EmbeddingGenerator, TokenHashEmbeddingGenerator
from app.similarity.pgvector_backend import PgVectorSimilarityBackend

__all__ = [
    "EmbeddingGenerator",
    "PgVectorSimilarityBackend",
    "SimilarityBackend",
    "SimilarityMatch",
    "TokenHashEmbeddingGenerator",
]
