import importlib
import importlib.util
from uuid import uuid4


def _load_similarity_module(module_name: str):
    qualified_name = f"app.similarity.{module_name}"
    try:
        module_spec = importlib.util.find_spec(qualified_name)
    except ModuleNotFoundError:
        module_spec = None
    assert module_spec is not None, (
        f"Step 0 similarity module is missing: {qualified_name}"
    )
    return importlib.import_module(qualified_name)


def test_similarity_backend_accepts_a_substitutable_fake():
    base = _load_similarity_module("base")
    source_id = uuid4()

    class FakeSimilarityBackend(base.SimilarityBackend):
        def find_similar(
            self,
            text,
            threshold,
            top_n,
            *,
            exclude_ids=(),
            statuses=None,
            item_type=None,
        ):
            assert text == "Improve rural water access"
            assert threshold == 0.95
            assert top_n == 5
            assert tuple(exclude_ids) == ()
            assert statuses is None
            assert item_type is None
            return [base.SimilarityMatch(source_id=source_id, score=0.99)]

    backend = FakeSimilarityBackend()

    assert backend.find_similar(
        "Improve rural water access",
        threshold=0.95,
        top_n=5,
    ) == [base.SimilarityMatch(source_id=source_id, score=0.99)]


def test_embedding_generator_returns_consistent_fixed_dimension_vectors():
    embeddings = _load_similarity_module("embeddings")
    generator = embeddings.TokenHashEmbeddingGenerator(dimension=384)

    first = generator.embed("Improve rural water access")
    second = generator.embed("Improve rural water access")

    assert generator.dimension == 384
    assert len(first) == 384
    assert first == second
    assert any(value != 0 for value in first)


def test_embedding_generator_handles_empty_text_without_nan_values():
    embeddings = _load_similarity_module("embeddings")
    generator = embeddings.TokenHashEmbeddingGenerator(dimension=384)

    vector = generator.embed("  ")

    assert len(vector) == 384
    assert vector == [0.0] * 384
