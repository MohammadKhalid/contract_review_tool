"""
Application configuration using Pydantic Settings.
Centralizes all environment variables and application constants.
"""

import os
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_TITLE: str = Field(
        default="German Rental Contract Review API", alias="APP_TITLE"
    )
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    # You can either set DATABASE_URL directly, or set the individual components
    # (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD) to auto-construct it.
    POSTGRES_DB: Optional[str] = Field(default=None, alias="POSTGRES_DB")
    POSTGRES_USER: Optional[str] = Field(default=None, alias="POSTGRES_USER")
    POSTGRES_PASSWORD: Optional[str] = Field(default=None, alias="POSTGRES_PASSWORD")
    DATABASE_URL: str = Field(
        default=None,
        alias="DATABASE_URL",
    )
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

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """
        If DATABASE_URL is not explicitly provided (is the default placeholder),
        construct it from POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD if set.
        """
        if self.POSTGRES_DB is not None:
            user = self.POSTGRES_USER
            password = self.POSTGRES_PASSWORD
            self.DATABASE_URL = (
                f"postgresql://{user}:{password}@db:5432/{self.POSTGRES_DB}"
            )
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # Allow POPO field names to be used alongside aliases
        "populate_by_name": True,
    }


settings = Settings()
