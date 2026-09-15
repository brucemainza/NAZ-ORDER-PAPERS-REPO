import hashlib
import math
import re
from abc import ABC, abstractmethod

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingGenerator(ABC):
    """Small interface for swappable text-embedding implementations."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the fixed number of values produced by ``embed``."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier for reproducibility."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Return a deterministic, fixed-dimension vector for ``text``."""


class TokenHashEmbeddingGenerator(EmbeddingGenerator):
    """Dependency-free signed feature hashing for NAZ text.

    Version 1 uses Python's standard-library BLAKE2b implementation to map
    normalized tokens into a fixed vector and L2-normalizes the result. It is
    deterministic, requires no model download, and can be replaced through the
    :class:`EmbeddingGenerator` contract when NAZ selects a learned model.
    """

    def __init__(self, dimension: int = 384) -> None:
        if dimension < 1:
            raise ValueError("Embedding dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return "naz-embed-v1"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = TOKEN_PATTERN.findall(text.casefold())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(
                token.encode("utf-8"),
                digest_size=16,
                person=b"naz-embed-v1",
            ).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]
