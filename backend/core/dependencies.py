"""
Reusable FastAPI dependencies.
Provides dependency injection for database sessions, NLP models, and embedding services.
"""

from typing import Iterator

import spacy
from fastapi import Depends
from sqlalchemy.orm import Session

from core.config import settings
from core.exceptions import AppException
from core.logging import get_logger
from database.connection import get_db as get_db_session
from legal_kb.embeddings import EmbeddingService

logger = get_logger(__name__)

# --- Database dependency ---


def get_db() -> Iterator[Session]:
    """Dependency that provides a database session."""
    yield from get_db_session()


# --- spaCy NLP model dependency ---

_nlp_instance = None


def get_nlp_model() -> spacy.Language:
    """
    Dependency that provides a shared spaCy NLP model (singleton).
    Loads the model on first call and caches it.
    """
    global _nlp_instance
    if _nlp_instance is None:
        logger.info("Loading spaCy model: %s", settings.SPACY_MODEL)
        try:
            _nlp_instance = spacy.load(settings.SPACY_MODEL)
        except OSError:
            logger.error(
                "spaCy model '%s' not found. Run: python -m spacy download %s",
                settings.SPACY_MODEL,
                settings.SPACY_MODEL,
            )
            raise AppException(
                message=f"spaCy model '{settings.SPACY_MODEL}' not installed",
                status_code=500,
            )
    return _nlp_instance


# --- Embedding service dependency ---

_embedding_service_instance = None


def get_embedding_service() -> EmbeddingService:
    """
    Dependency that provides a shared EmbeddingService instance (singleton).
    """
    global _embedding_service_instance
    if _embedding_service_instance is None:
        logger.info("Initializing embedding service: %s", settings.EMBEDDING_MODEL)
        _embedding_service_instance = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL
        )
    return _embedding_service_instance
