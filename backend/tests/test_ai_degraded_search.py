from app.ai.schemas import SimilaritySearchRequest
from app.ai.service import AISimilarityService
from app.config import Settings


class EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class EmptyDatabase:
    def execute(self, _query):
        return EmptyResult()

    def scalar(self, _query):
        return 0


class OfflineEmbeddingProvider:
    model_name = "offline-model"

    def embed_query(self, _text):
        raise RuntimeError("Ollama is unavailable")


class VisibleUser:
    id = None

    def has_permission(self, _permission):
        return True


def test_hybrid_search_degrades_to_lexical_when_embedding_is_unavailable():
    settings = Settings()
    service = AISimilarityService(
        db=EmptyDatabase(),
        user=VisibleUser(),
        settings=settings,
        embedding_provider=OfflineEmbeddingProvider(),
    )

    response = service.search(SimilaritySearchRequest(query_text="rural water"))

    assert response.results == []
    assert response.retrieval_mode == "lexical"
    assert response.degraded is True
    assert response.warnings == ["Semantic retrieval is temporarily unavailable."]
