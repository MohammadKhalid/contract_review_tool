"""
Legal Knowledge Base API endpoints.
Provides access to German rental law documents, vector search, and invalid clause detection.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from models.legal_kb import LegalSource, LegalChunk
from legal_kb.ingestion import (
    ingest_seed_sources,
    ingest_seed_documents,
    ingest_seed_invalid_clauses,
    get_kb_stats,
)
from legal_kb.retrieval import (
    search_legal_knowledge,
    get_invalid_clause_patterns,
    check_clause_against_patterns,
    get_legal_sources,
    get_legal_documents,
)
from legal_kb.seed_data import (
    get_seed_sources,
    get_seed_documents,
    get_seed_invalid_clauses,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/legal-kb", tags=["legal-knowledge-base"])


@router.post("/seed")
async def seed_legal_knowledge_base(db: Session = Depends(get_db)):
    """
    Initialize the legal knowledge base with German rental law content.
    This should be run once after the application starts.
    """
    try:
        logger.info("Starting legal knowledge base seeding...")

        # Seed sources
        source_ids = ingest_seed_sources(db)
        sources_created = len(source_ids)
        logger.info(f"Seeded {sources_created} legal sources")

        # Seed documents
        document_ids = ingest_seed_documents(db, source_ids)
        documents_created = len(document_ids)
        logger.info(f"Seeded {documents_created} legal documents")

        # Seed invalid clause patterns
        invalid_clause_ids = ingest_seed_invalid_clauses(db, source_ids)
        invalid_clauses_created = len(invalid_clause_ids)
        logger.info(f"Seeded {invalid_clauses_created} invalid clause patterns")

        # Embeddings created during document ingestion
        embeddings_created = db.query(LegalChunk).count()
        logger.info(f"Generated embeddings for {embeddings_created} document chunks")

        return {
            "message": "Legal knowledge base seeded successfully",
            "sources_created": sources_created,
            "documents_created": documents_created,
            "invalid_clauses_created": invalid_clauses_created,
            "embeddings_created": embeddings_created,
        }

    except Exception as e:
        logger.error(f"Error seeding legal knowledge base: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to seed legal knowledge base: {str(e)}"
        )


@router.get("/stats")
async def get_legal_kb_stats(db: Session = Depends(get_db)):
    """Get statistics about the legal knowledge base."""
    try:
        stats = get_kb_stats(db)
        return stats

    except Exception as e:
        logger.error(f"Error getting legal KB stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal KB stats: {str(e)}"
        )


@router.post("/search")
async def search_legal_documents(
    query: str = Query(..., description="Search query for legal documents"),
    limit: int = Query(10, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
):
    """
    Perform semantic search over legal documents using vector similarity.
    Returns relevant legal sections and their similarity scores.
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")

        results = search_legal_knowledge(db, query, limit)
        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching legal documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to search legal documents: {str(e)}"
        )


@router.get("/invalid-clauses")
async def get_invalid_clause_patterns(
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
        patterns = get_invalid_clause_patterns(db, topic, risk_level)
        return {"patterns": patterns}

    except Exception as e:
        logger.error(f"Error getting invalid clause patterns: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get invalid clause patterns: {str(e)}"
        )


@router.post("/check-clause")
async def check_contract_clause(
    clause_text: str = Query(..., description="Contract clause text to check"),
    db: Session = Depends(get_db),
):
    """
    Check if a contract clause matches known invalid patterns.
    Returns potential issues and legal references.
    """
    try:
        if not clause_text or not clause_text.strip():
            raise HTTPException(status_code=400, detail="Clause text cannot be empty")

        result = check_clause_against_patterns(db, clause_text)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking contract clause: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to check contract clause: {str(e)}"
        )


@router.get("/sources")
async def get_legal_sources(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    db: Session = Depends(get_db),
):
    """Get list of legal sources."""
    try:
        sources = get_legal_sources(db, source_type)
        return {"sources": sources}

    except Exception as e:
        logger.error(f"Error getting legal sources: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal sources: {str(e)}"
        )


@router.get("/documents")
async def get_legal_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    source_title: Optional[str] = Query(None, description="Filter by source title"),
    limit: int = Query(50, description="Maximum number of documents to return"),
    db: Session = Depends(get_db),
):
    """Get list of legal documents."""
    try:
        if source_title:
            source = (
                db.query(LegalSource).filter(LegalSource.title == source_title).first()
            )
            if not source:
                raise HTTPException(status_code=404, detail="Source not found")
            source_id = source.id
        else:
            source_id = None

        documents = get_legal_documents(
            db, source_id=source_id, category=category, limit=limit
        )
        return {"documents": documents}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting legal documents: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get legal documents: {str(e)}"
        )
