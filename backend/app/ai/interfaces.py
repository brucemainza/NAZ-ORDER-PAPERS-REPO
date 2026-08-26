from abc import ABC, abstractmethod

from app.ai.schemas import AIExplanation, RecordMatch, SimilaritySearchRequest


class EmbeddingProvider(ABC):
    """Abstract provider for text embeddings."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension produced by this provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier for reproducibility."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document strings."""


class SemanticRetriever(ABC):
    """Retrieve candidates using vector similarity over a pgvector index."""

    @abstractmethod
    def search(
        self,
        request: SimilaritySearchRequest,
        query_embedding: list[float],
        k: int,
    ) -> list[RecordMatch]:
        """Return ranked semantic matches."""


class LexicalRetriever(ABC):
    """Retrieve candidates using PostgreSQL full-text search."""

    @abstractmethod
    def search(
        self,
        request: SimilaritySearchRequest,
        k: int,
    ) -> list[RecordMatch]:
        """Return ranked lexical matches."""


class RankFusion(ABC):
    """Combine ranked lists into a single ranked list."""

    @abstractmethod
    def combine(self, *ranked_lists: list[RecordMatch]) -> list[RecordMatch]:
        """Merge and return a fused ranked list."""


class ExplanationProvider(ABC):
    """Generate a grounded explanation from retrieved evidence."""

    @abstractmethod
    def explain(
        self,
        query_text: str,
        evidence: list[dict],
    ) -> AIExplanation:
        """Return a structured explanation grounded in the supplied evidence."""
