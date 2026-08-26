from unittest.mock import Mock

import httpx

from app.ai.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.config import Settings


def _settings() -> Settings:
    settings = Settings()
    settings.ollama_base_url = "http://localhost:11434"
    settings.ollama_embedding_model = "embeddinggemma:300m"
    settings.ai_embedding_dimension = 768
    settings.ai_request_timeout = 30
    settings.ai_connect_timeout = 2
    settings.ai_max_retries = 1
    settings.ai_circuit_break_seconds = 30
    return settings


def _response(json_data, status_code=200):
    return httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("POST", "http://localhost:11434/api/embed"),
    )


def test_ollama_embedding_provider_returns_768_dim_vector():
    settings = _settings()
    client = Mock()
    provider = OllamaEmbeddingProvider(settings, client=client)

    fake_vector = [0.1] * 768
    client.post.return_value = _response({"embeddings": [fake_vector]})
    result = provider.embed_query("test query")

    assert len(result) == 768
    assert result[0] == 0.1
    client.post.assert_called_once_with(
        "/api/embed",
        json={
            "model": "embeddinggemma:300m",
            "input": ["test query"],
        },
    )


def test_ollama_embedding_provider_rejects_dimension_mismatch():
    settings = _settings()
    client = Mock()
    provider = OllamaEmbeddingProvider(settings, client=client)

    fake_vector = [0.1] * 384
    client.post.return_value = _response({"embeddings": [fake_vector]})
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


def test_ollama_embedding_provider_batches_documents_in_one_request():
    settings = _settings()
    client = Mock()
    provider = OllamaEmbeddingProvider(settings, client=client)
    vectors = [[0.1] * 768, [0.2] * 768]
    client.post.return_value = _response({"embeddings": vectors})

    result = provider.embed_documents([" first  document ", "second document"])

    assert result == vectors
    client.post.assert_called_once_with(
        "/api/embed",
        json={
            "model": "embeddinggemma:300m",
            "input": ["first document", "second document"],
        },
    )


def test_ollama_embedding_provider_opens_circuit_after_bounded_retries():
    settings = _settings()
    client = Mock()
    client.post.side_effect = httpx.ConnectError("offline")
    provider = OllamaEmbeddingProvider(settings, client=client, sleep=lambda _: None)

    for expected_calls in (2, 2):
        try:
            provider.embed_query("test query")
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
        assert client.post.call_count == expected_calls
