import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.ai.interfaces import EmbeddingProvider
from app.ai.normalization import normalize_for_embedding
from app.config import Settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider that calls a local Ollama instance.

    Uses the /api/embeddings endpoint so the same Ollama process can serve
    both embeddings and generation models. This keeps the stack local-only
    and government-network friendly.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_embedding_model
        self._dimension = settings.ai_embedding_dimension
        self._max_retries = settings.ai_max_retries
        self._circuit_break_seconds = settings.ai_circuit_break_seconds
        self._sleep = sleep
        self._clock = clock
        self._circuit_until = 0.0
        self._circuit_lock = threading.Lock()
        self._client = client or httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(
                settings.ai_request_timeout,
                connect=settings.ai_connect_timeout,
            ),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    def embed_query(self, text: str) -> list[float]:
        results = self.embed_documents([text])
        if not results:
            return [0.0] * self._dimension
        return results[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        cleaned = [normalize_for_embedding(text) for text in texts]
        if not cleaned:
            return []

        nonempty_positions = [index for index, text in enumerate(cleaned) if text]
        requested = [cleaned[index] for index in nonempty_positions]
        requested_vectors = self._request_embeddings(requested) if requested else []
        results = [[0.0] * self._dimension for _ in cleaned]
        for position, vector in zip(nonempty_positions, requested_vectors, strict=True):
            if len(vector) != self._dimension:
                logger.error(
                    "Embedding dimension mismatch for model %s: expected %d, got %d",
                    self._model,
                    self._dimension,
                    len(vector),
                )
                raise RuntimeError(
                    f"Embedding dimension mismatch: expected {self._dimension}, got {len(vector)}"
                )
            results[position] = vector
        return results

    def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        self._ensure_circuit_closed()
        payload: dict[str, Any] = {
            "model": self._model,
            "input": texts,
        }
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.post("/api/embed", json=payload)
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings")
                if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                    raise ValueError("invalid embedding batch response")
                with self._circuit_lock:
                    self._circuit_until = 0.0
                return [
                    [float(value) for value in embedding]
                    for embedding in embeddings
                ]
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                last_error = exc
                if attempt < self._max_retries:
                    self._sleep(min(0.25 * (2**attempt), 1.0))

        with self._circuit_lock:
            self._circuit_until = self._clock() + self._circuit_break_seconds
        logger.warning("Ollama embedding request failed after retries: %s", last_error)
        raise RuntimeError(
            f"Could not generate embeddings with Ollama at {self._base_url}"
        ) from last_error

    def _ensure_circuit_closed(self) -> None:
        with self._circuit_lock:
            if self._circuit_until > self._clock():
                raise RuntimeError("Ollama embedding circuit is temporarily open")
