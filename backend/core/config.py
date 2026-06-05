"""
Application configuration using Pydantic Settings.
Centralizes all environment variables and application constants.
"""

import json
import os
from typing import List, Optional, Union, Any

from pydantic import Field, field_validator, model_validator
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

    # --- Flexible list parsing for env vars (supports both JSON and comma-separated) ---
    @field_validator(
        "CORS_ORIGINS",
        "CORS_METHODS",
        "CORS_HEADERS",
        "ALLOWED_EXTENSIONS",
        mode="before",
    )
    @classmethod
    def parse_csv_or_json_list(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                # Try JSON first: '["https://example.com"]' or ["https://example.com"]
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except (json.JSONDecodeError, TypeError):
                pass
            # Fallback to comma-separated: https://example.com,https://other.com
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return v

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

    # Pattern matching (rule-based minimal checks)
    CLAUSE_MIN_LENGTH: int = 20
    PATTERN_SIMILARITY_THRESHOLD: float = 0.8
    MAX_ISSUES: int = 10

    # xAI / LLM Judge
    XAI_API_KEY: str = Field(default="", alias="XAI_API_KEY")
    XAI_MODEL: str = Field(default="grok-4.3", alias="XAI_MODEL")
    LLM_SEARCH_LIMIT: int = 3
    LLM_CONFIDENCE_THRESHOLD: float = 0.6

    # LLM / Parallelism tuning (new for performance)
    LLM_CONCURRENCY: int = 6          # Max concurrent LLM calls
    LLM_JUDGE_THRESHOLD: float = 0.75 # Higher threshold to decide whether to call the expensive LLM judge
    LLM_BATCH_SIZE: int = 3           # Number of clauses to judge in one LLM call (reduces round-trips)

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Admin Authentication (static key for internal/admin access, bypasses Polar)
    ADMIN_API_KEY: str = Field(default="", alias="ADMIN_API_KEY")

    # Polar.sh Paywall & License Key Integration
    # Get these from your Polar organization settings after creating a one-time Product + License Key benefit.
    # Use POLAR_SERVER=sandbox for testing (default). Switch to "production" for live sales.
    POLAR_ACCESS_TOKEN: str = Field(default="", alias="POLAR_ACCESS_TOKEN")
    POLAR_ORGANIZATION_ID: str = Field(default="", alias="POLAR_ORGANIZATION_ID")
    POLAR_SERVER: str = Field(default="sandbox", alias="POLAR_SERVER")  # "sandbox" or "production"
    POLAR_ANALYSIS_PRODUCT_ID: Optional[str] = Field(default=None, alias="POLAR_ANALYSIS_PRODUCT_ID")

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
