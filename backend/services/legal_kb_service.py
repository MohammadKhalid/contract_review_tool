"""
Legal Knowledge Base service.
Provides high-level operations for legal KB operations,
wrapping the ingestion and retrieval modules.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.logging import get_logger
from legal_kb.ingestion import (
    ingest_seed_sources,
    ingest_seed_documents,
    ingest_seed_invalid_clauses,
    ingest_seed_bgh_rulings,
    clear_legal_knowledge_base,
    get_kb_stats,
)
from legal_kb.retrieval import (
    search_legal_knowledge as retrieval_search,
    get_invalid_clause_patterns as retrieval_get_patterns,
    check_clause_against_patterns as retrieval_check_clause,
    get_legal_sources as retrieval_get_sources,
    get_legal_documents as retrieval_get_documents,
)
from legal_kb.embeddings import EmbeddingService
from schemas.legal_kb import (
    InvalidClausePattern,
    InvalidClauseCheckResponse,
    KBStatsResponse,
    SeedResponse,
    SearchResponse,
)

logger = get_logger(__name__)


def seed_knowledge_base(
    db: Session,
    embedding_service: EmbeddingService,
    reset: bool = False,
) -> SeedResponse:
    """
    Seed the legal knowledge base with initial data.

    Args:
        db: Database session
        embedding_service: Embedding service for generating vector embeddings
        reset: If True, clear existing data before seeding

    Returns:
        SeedResponse with counts of created items
    """
    logger.info(
        "Starting legal knowledge base seeding%s...", " with reset" if reset else ""
    )

    records_deleted = None
    if reset:
        logger.warning("Reset requested: clearing all existing legal KB data...")
        records_deleted = clear_legal_knowledge_base(db)
        logger.info("Clear completed")

    source_ids = ingest_seed_sources(db)
    sources_created = len(source_ids)
    logger.info("Seeded %d legal sources", sources_created)

    document_ids = ingest_seed_documents(db, source_ids)
    documents_created = len(document_ids)
    logger.info("Seeded %d legal documents", documents_created)

    bgh_ids = ingest_seed_bgh_rulings(db, source_ids)
    bgh_rulings_created = len(bgh_ids)
    logger.info("Seeded %d BGH rulings", bgh_rulings_created)

    invalid_clause_ids = ingest_seed_invalid_clauses(db, source_ids)
    invalid_clauses_created = len(invalid_clause_ids)
    logger.info("Seeded %d invalid clause patterns", invalid_clauses_created)

    from models.legal_kb import LegalChunk

    embeddings_created = db.query(LegalChunk).count()
    logger.info("Generated embeddings for %d document chunks", embeddings_created)

    return SeedResponse(
        message=(
            "Legal knowledge base seeded successfully"
            if not reset
            else "Legal knowledge base reset and re-seeded successfully"
        ),
        sources_created=sources_created,
        documents_created=documents_created,
        bgh_rulings_created=bgh_rulings_created,
        invalid_clauses_created=invalid_clauses_created,
        embeddings_created=embeddings_created,
        reset_performed=reset,
        records_deleted=records_deleted,
    )


def get_statistics(db: Session) -> KBStatsResponse:
    """Get statistics about the legal knowledge base."""
    stats = get_kb_stats(db)
    return KBStatsResponse(**stats)


def search_documents(db: Session, query: str, limit: int = 10) -> SearchResponse:
    """
    Perform semantic search over legal documents.

    Args:
        db: Database session
        query: Search query text
        limit: Maximum number of results

    Returns:
        SearchResponse with matching documents
    """
    results = retrieval_search(db, query, limit)
    return SearchResponse(**results)


def get_invalid_clause_patterns(
    db: Session,
    topic: Optional[str] = None,
    risk_level: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get known invalid clause patterns, optionally filtered.

    Args:
        db: Database session
        topic: Filter by topic
        risk_level: Filter by risk level

    Returns:
        Dict with patterns list
    """
    patterns = retrieval_get_patterns(db, topic, risk_level)
    return {"patterns": patterns}


def check_clause(db: Session, clause_text: str) -> InvalidClauseCheckResponse:
    """
    Check a contract clause against known invalid patterns.

    Args:
        db: Database session
        clause_text: The clause text to check

    Returns:
        InvalidClauseCheckResponse with matches
    """
    matches = retrieval_check_clause(db, clause_text)
    return InvalidClauseCheckResponse(matches=matches)


def get_sources(
    db: Session, source_type: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Get list of legal sources."""
    sources = retrieval_get_sources(db, source_type)
    return {"sources": sources}


def get_documents(
    db: Session,
    category: Optional[str] = None,
    source_title: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, List[Dict[str, Any]]]:
    """Get list of legal documents."""
    from models.legal_kb import LegalSource

    source_id = None
    if source_title:
        source = db.query(LegalSource).filter(LegalSource.title == source_title).first()
        if not source:
            from core.exceptions import NotFoundException

            raise NotFoundException("Source", source_title)
        source_id = source.id

    documents = retrieval_get_documents(
        db, source_id=source_id, category=category, limit=limit
    )
    return {"documents": documents}
