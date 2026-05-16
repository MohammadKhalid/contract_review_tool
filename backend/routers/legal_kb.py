"""
Legal Knowledge Base API endpoints.
Thin router that delegates business logic to the legal KB service.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from core.dependencies import get_db, get_embedding_service
from core.exceptions import AppException, BadRequestException, NotFoundException
from core.logging import get_logger
from legal_kb.embeddings import EmbeddingService
from schemas.legal_kb import (
    InvalidClauseCheckResponse,
    InvalidClausePattern,
    KBStatsResponse,
    SeedResponse,
    SearchResponse,
)
from services.legal_kb_service import (
    seed_knowledge_base,
    get_statistics,
    search_documents,
    get_invalid_clause_patterns,
    check_clause,
    get_sources,
    get_documents,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/legal-kb", tags=["legal-knowledge-base"])


@router.post(
    "/seed",
    response_model=SeedResponse,
    summary="Initialize legal knowledge base",
    description="Seed the legal knowledge base with German rental law content.",
)
async def seed_legal_knowledge_base(
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Initialize the legal knowledge base with German rental law content."""
    try:
        return seed_knowledge_base(db, embedding_service)
    except Exception as e:
        logger.error("Error seeding legal knowledge base: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to seed legal knowledge base: {str(e)}"
        )


@router.get(
    "/stats",
    response_model=KBStatsResponse,
    summary="Get legal KB statistics",
)
async def get_legal_kb_stats(db: Session = Depends(get_db)):
    """Get statistics about the legal knowledge base."""
    try:
        return get_statistics(db)
    except Exception as e:
        logger.error("Error getting legal KB stats: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal KB stats: {str(e)}"
        )


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search legal documents",
    description="Perform semantic search over legal documents using vector similarity.",
)
async def search_legal_documents(
    query: str = Query(..., description="Search query for legal documents"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
):
    """Perform semantic search over legal documents."""
    try:
        if not query or not query.strip():
            raise BadRequestException("Query cannot be empty")
        return search_documents(db, query, limit)
    except BadRequestException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Error searching legal documents: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to search legal documents: {str(e)}"
        )


@router.get(
    "/invalid-clauses",
    summary="Get invalid clause patterns",
    description="Get list of known invalid clause patterns, optionally filtered.",
)
async def get_invalid_clause_patterns_endpoint(
    topic: Optional[str] = Query(
        None, description="Filter by topic (e.g., 'Kaution', 'Kündigung')"
    ),
    risk_level: Optional[str] = Query(
        None, description="Filter by risk level ('high', 'medium', 'low')"
    ),
    db: Session = Depends(get_db),
):
    """Get list of known invalid clause patterns."""
    try:
        return get_invalid_clause_patterns(db, topic, risk_level)
    except Exception as e:
        logger.error("Error getting invalid clause patterns: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get invalid clause patterns: {str(e)}"
        )


@router.post(
    "/check-clause",
    response_model=InvalidClauseCheckResponse,
    summary="Check a clause against invalid patterns",
    description="Check if a contract clause matches known invalid patterns.",
)
async def check_contract_clause(
    clause_text: str = Query(..., description="Contract clause text to check"),
    db: Session = Depends(get_db),
):
    """Check if a contract clause matches known invalid patterns."""
    try:
        if not clause_text or not clause_text.strip():
            raise BadRequestException("Clause text cannot be empty")
        return check_clause(db, clause_text)
    except BadRequestException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Error checking contract clause: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to check contract clause: {str(e)}"
        )


@router.get(
    "/sources",
    summary="Get legal sources",
    description="Get list of legal sources, optionally filtered by type.",
)
async def get_legal_sources_endpoint(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    db: Session = Depends(get_db),
):
    """Get list of legal sources."""
    try:
        return get_sources(db, source_type)
    except Exception as e:
        logger.error("Error getting legal sources: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal sources: {str(e)}"
        )


@router.get(
    "/documents",
    summary="Get legal documents",
    description="Get list of legal documents, optionally filtered.",
)
async def get_legal_documents_endpoint(
    category: Optional[str] = Query(None, description="Filter by category"),
    source_title: Optional[str] = Query(None, description="Filter by source title"),
    limit: int = Query(50, description="Maximum number of documents to return"),
    db: Session = Depends(get_db),
):
    """Get list of legal documents."""
    try:
        return get_documents(db, category, source_title, limit)
    except NotFoundException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Error getting legal documents: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal documents: {str(e)}"
        )
