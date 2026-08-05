from unittest.mock import patch

import httpx

from app.ai.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.config import Settings


def _settings() -> Settings:
    settings = Settings()
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_embedding_model = "embeddinggemma:300m"
    settings.ai_embedding_dimension = 768
    settings.ai_request_timeout = 30
    return settings


def _response(json_data, status_code=200):
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("POST", "http://localhost:11434/api/embeddings"),
    )


def test_ollama_embedding_provider_returns_768_dim_vector():
    settings = _settings()
    provider = OllamaEmbeddingProvider(settings)

    fake_vector = [0.1] * 768
    with patch.object(
        httpx,
        "post",
        return_value=_response({"embedding": fake_vector}),
    ):
        result = provider.embed_query("test query")

    assert len(result) == 768
    assert result[0] == 0.1


def test_ollama_embedding_provider_rejects_dimension_mismatch():
    settings = _settings()
    provider = OllamaEmbeddingProvider(settings)

    fake_vector = [0.1] * 384
    with patch.object(
        httpx,
        "post",
        return_value=_response({"embedding": fake_vector}),
    ):
        try:
            provider.embed_query("test query")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "768" in str(exc)


def test_ollama_embedding_provider_model_name():
    settings = _settings()
    provider = OllamaEmbeddingProvider(settings)
    assert provider.model_name == "embeddinggemma:300m"
    assert provider.dimension == 768
