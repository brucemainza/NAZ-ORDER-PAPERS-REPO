from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.ai.interfaces import EmbeddingProvider
from app.ai.service import AISimilarityService
from app.config import Settings, get_settings
from app.database import get_db
from app.deps import get_current_user


@lru_cache
def get_ai_settings() -> Settings:
    return get_settings()


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return OllamaEmbeddingProvider(get_ai_settings())


def get_ai_service(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    settings: Settings = Depends(get_ai_settings),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> AISimilarityService:
    return AISimilarityService(
        db=db,
        user=user,
        settings=settings,
        embedding_provider=embedding_provider,
    )
