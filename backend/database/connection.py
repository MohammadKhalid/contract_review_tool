from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@db:5432/contract_db"
)

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
    """Create all database tables"""
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()

    # Import models to register them with SQLAlchemy
    from models.contract import Contract, ContractAnalysis
    from models.legal_kb import (
        LegalSource,
        LegalDocument,
        LegalChunk,
        InvalidClausePattern,
    )

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def get_db_session():
    """Get a database session for manual use"""
    return SessionLocal()
