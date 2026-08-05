import logging
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

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_embedding_model
        self._dimension = settings.ai_embedding_dimension
        self._timeout = settings.ai_request_timeout

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
        results: list[list[float]] = []
        for text in cleaned:
            vector = self._request_embedding(text)
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
            results.append(vector)
        return results

    def _request_embedding(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self._dimension

        url = f"{self._base_url}/api/embeddings"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": text,
        }

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.exception("Ollama embedding HTTP error")
            raise RuntimeError(
                f"Ollama embedding request failed: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.exception("Ollama embedding request error")
            raise RuntimeError(
                f"Could not reach Ollama at {self._base_url}: {exc}"
            ) from exc

        embedding = data.get("embedding")
        if not embedding or not isinstance(embedding, list):
            raise RuntimeError(f"Invalid embedding response from Ollama: {data}")

        return [float(value) for value in embedding]
