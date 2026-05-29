from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

# Database URL from centralized configuration
DATABASE_URL = settings.DATABASE_URL

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Legacy table creation using SQLAlchemy metadata.

    This path is only used when AUTO_CREATE_TABLES=true.
    The recommended mechanism is Alembic migrations (see docker-entrypoint.sh).
    """
    # Enable pgvector extension (safe to run repeatedly)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    # Import models to register them with SQLAlchemy (required for create_all)
    from models.contract import Contract, ContractAnalysis
    from models.legal_kb import (
        LegalSource,
        LegalDocument,
        LegalChunk,
        InvalidClausePattern,
    )

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully (via legacy create_all path)")


def get_db_session():
    """Get a database session for manual use"""
    return SessionLocal()
