"""Swappable embedding and similarity-search contracts."""

from app.similarity.base import SimilarityBackend, SimilarityMatch
from app.similarity.embeddings import EmbeddingGenerator, TokenHashEmbeddingGenerator

__all__ = [
    "EmbeddingGenerator",
    "SimilarityBackend",
    "SimilarityMatch",
    "TokenHashEmbeddingGenerator",
]
