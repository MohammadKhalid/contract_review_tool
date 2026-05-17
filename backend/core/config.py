"""
Application configuration using Pydantic Settings.
Centralizes all environment variables and application constants.
"""

import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_TITLE: str = "German Rental Contract Review API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DB = os.getenv("POSTGRES_DB", None)
    USERNAME = os.getenv("POSTGRES_USER", "user")
    PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    DATABASE_URL = f"postgresql://{USERNAME}:{PASSWORD}@db:5432/{DB}"
    DATABASE_ECHO: bool = False

    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # Upload
    UPLOAD_DIR: str = "uploads/contracts"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]

    # spaCy
    SPACY_MODEL: str = "de_core_news_sm"

    # Embeddings
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384

    # Chunking
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # Vector search
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7
    VECTOR_SEARCH_LIMIT: int = 5

    # Pattern matching
    CLAUSE_MIN_LENGTH: int = 20
    PATTERN_SIMILARITY_THRESHOLD: float = 0.8
    MAX_ISSUES: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
