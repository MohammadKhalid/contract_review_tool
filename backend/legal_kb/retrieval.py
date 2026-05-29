"""
Retrieval module for legal knowledge base.
Handles vector search and retrieval of relevant legal information.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
import logging

from models.legal_kb import LegalSource, LegalDocument, LegalChunk, InvalidClausePattern
from legal_kb.embeddings import embedding_service

logger = logging.getLogger(__name__)


def search_similar_chunks(
    db: Session,
    query_embedding: np.ndarray,
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Search for legal chunks similar to the query embedding using vector similarity.

    Args:
        db: Database session
        query_embedding: Query embedding vector
        limit: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0-1)

    Returns:
        List of similar chunks with metadata
    """
    # Convert embedding to list for PostgreSQL
    embedding_list = query_embedding.tolist()

    # Perform vector similarity search
    sql = text("""
        SELECT
            lc.id,
            lc.document_id,
            lc.chunk_index,
            lc.text,
            lc.token_count,
            lc.embedding <=> :query_embedding as similarity,
            ld.title as document_title,
            ld.citation,
            ld.category,
            ld.summary,
            ls.title as source_title,
            ls.source_type,
            ls.publisher
        FROM legal_chunks lc
        JOIN legal_documents ld ON lc.document_id = ld.id
        JOIN legal_sources ls ON ld.source_id = ls.id
        WHERE lc.embedding <=> :query_embedding < :threshold
        ORDER BY lc.embedding <=> :query_embedding
        LIMIT :limit
    """)

    result = db.execute(
        sql,
        {
            "query_embedding": embedding_list,
            "threshold": 1.0
            - similarity_threshold,  # pgvector uses L2 distance, convert to similarity
            "limit": limit,
        },
    )

    chunks = []
    for row in result:
        chunks.append(
            {
                "chunk_id": row.id,
                "document_id": row.document_id,
                "chunk_index": row.chunk_index,
                "text": row.text,
                "token_count": row.token_count,
                "similarity": 1.0 - row.similarity,  # Convert back to similarity score
                "document_title": row.document_title,
                "citation": row.citation,
                "category": row.category,
                "summary": row.summary,
                "source_title": row.source_title,
                "source_type": row.source_type,
                "publisher": row.publisher,
            }
        )

    return chunks


def search_legal_knowledge(
    db: Session, query: str, limit: int = 5, similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Search the legal knowledge base for information relevant to a query.

    Args:
        db: Database session
        query: Search query text
        limit: Maximum number of results
        similarity_threshold: Minimum similarity threshold

    Returns:
        Search results with chunks and metadata
    """
    # Generate embedding for the query
    query_embedding = embedding_service.encode_single(query)

    # Search for similar chunks
    similar_chunks = search_similar_chunks(
        db, query_embedding, limit, similarity_threshold
    )

    # Group results by document for better presentation
    documents = {}
    for chunk in similar_chunks:
        doc_id = chunk["document_id"]
        if doc_id not in documents:
            documents[doc_id] = {
                "document_id": doc_id,
                "title": chunk["document_title"],
                "citation": chunk["citation"],
                "category": chunk["category"],
                "summary": chunk["summary"],
                "source_title": chunk["source_title"],
                "source_type": chunk["source_type"],
                "publisher": chunk["publisher"],
                "chunks": [],
            }
        documents[doc_id]["chunks"].append(
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "similarity": chunk["similarity"],
                "token_count": chunk["token_count"],
            }
        )

    return {
        "query": query,
        "total_results": len(similar_chunks),
        "documents": list(documents.values()),
        "search_parameters": {
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        },
    }


def retrieve_top_invalid_patterns(
    db: Session,
    section_embedding: np.ndarray,
    limit: int = 3,
    similarity_threshold: float = 0.6,
) -> List[Dict[str, Any]]:
    """
    Retrieve top-N most relevant invalid clause patterns for a section using vector search.

    Uses the pre-computed embeddings on invalid_clause_patterns table.
    This replaces the old in-memory brute-force check in check_clause_against_patterns.

    Args:
        db: Database session
        section_embedding: Embedding vector of the contract section.
        limit: Maximum number of patterns to return (default 3).
        similarity_threshold: Minimum similarity (0-1) for a pattern to be considered.

    Returns:
        List of top matching invalid clause patterns with similarity and metadata.
    """
    embedding_list = section_embedding.tolist()

    sql = text("""
        SELECT
            id,
            topic,
            clause_pattern,
            why_invalid,
            legal_basis,
            risk_level,
            example_text,
            recommended_response,
            bgb_citation,
            bgb_text_excerpt,
            embedding <=> :query_embedding as distance
        FROM invalid_clause_patterns
        WHERE embedding IS NOT NULL
          AND embedding <=> :query_embedding < :threshold
        ORDER BY embedding <=> :query_embedding
        LIMIT :limit
    """)

    result = db.execute(
        sql,
        {
            "query_embedding": embedding_list,
            "threshold": 1.0 - similarity_threshold,
            "limit": limit,
        },
    )

    patterns = []
    for row in result:
        patterns.append(
            {
                "id": row.id,
                "topic": row.topic,
                "clause_pattern": row.clause_pattern,
                "why_invalid": row.why_invalid,
                "legal_basis": row.legal_basis,
                "risk_level": row.risk_level,
                "example_text": row.example_text,
                "recommended_response": row.recommended_response,
                "bgb_citation": row.bgb_citation,
                "bgb_text_excerpt": row.bgb_text_excerpt,
                "similarity": 1.0 - row.distance,
            }
        )

    logger.info("Retrieved %d relevant invalid patterns for section", len(patterns))
    return patterns


def retrieve_bgb_excerpts_for_patterns(
    db: Session,
    patterns: List[Dict[str, Any]],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Retrieve exact BGB text excerpts relevant to the matched patterns.
    Searches legal_documents / legal_chunks for citations matching the pattern's legal_basis.

    Args:
        db: Database session
        patterns: List of matched invalid clause patterns (from retrieve_top_invalid_patterns).
        limit: Maximum number of BGB excerpts to return.

    Returns:
        List of BGB legal text excerpts with citations.
    """
    citations = set()
    for p in patterns:
        legal_basis = p.get("legal_basis") or p.get("bgb_citation") or ""
        # Extract BGB § references like "BGB § 551" or "BGB § 551 Abs. 3"
        import re

        matches = re.findall(r"BGB § \d+[a-z]?(?: Abs\. \d+)?", legal_basis)
        for m in matches:
            citations.add(m)
        if p.get("bgb_citation"):
            citations.add(p["bgb_citation"])

    if not citations:
        return []

    excerpts = []
    for citation in citations:
        # Try to find by citation in legal_documents
        doc = db.query(LegalDocument).filter(LegalDocument.citation == citation).first()
        if doc:
            excerpts.append(
                {
                    "citation": doc.citation,
                    "title": doc.title,
                    "text": doc.text[:1000],
                    "summary": doc.summary,
                }
            )
            if len(excerpts) >= limit:
                break

        # Fallback: search by keyword in citation
        if not doc:
            like_pattern = f"%{citation.replace('BGB § ', '')}%"
            docs = (
                db.query(LegalDocument)
                .filter(LegalDocument.citation.ilike(like_pattern))
                .limit(limit - len(excerpts))
                .all()
            )
            for d in docs:
                excerpts.append(
                    {
                        "citation": d.citation,
                        "title": d.title,
                        "text": d.text[:1000],
                        "summary": d.summary,
                    }
                )
                if len(excerpts) >= limit:
                    break

    return excerpts[:limit]


def get_invalid_clause_patterns(
    db: Session,
    topic: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Retrieve invalid clause patterns, optionally filtered by topic or risk level.

    Args:
        db: Database session
        topic: Filter by specific topic (e.g., 'Kaution', 'Kündigung')
        risk_level: Filter by risk level ('high', 'medium', 'low')
        limit: Maximum number of results

    Returns:
        List of invalid clause patterns
    """
    query = db.query(InvalidClausePattern)

    if topic:
        query = query.filter(InvalidClausePattern.topic == topic)

    if risk_level:
        query = query.filter(InvalidClausePattern.risk_level == risk_level)

    clauses = query.limit(limit).all()

    return [
        {
            "id": clause.id,
            "topic": clause.topic,
            "clause_pattern": clause.clause_pattern,
            "why_invalid": clause.why_invalid,
            "legal_basis": clause.legal_basis,
            "risk_level": clause.risk_level,
            "example_text": clause.example_text,
            "recommended_response": clause.recommended_response,
        }
        for clause in clauses
    ]


def check_clause_against_patterns(
    db: Session, clause_text: str, similarity_threshold: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Check if a contract clause matches known invalid patterns.

    Args:
        db: Database session
        clause_text: The contract clause text to check
        similarity_threshold: Minimum similarity for pattern matching

    Returns:
        List of matching invalid clause patterns with similarity scores
    """
    # Get all invalid clause patterns
    patterns = get_invalid_clause_patterns(db)

    matches = []
    clause_embedding = embedding_service.encode_single(clause_text)

    for pattern in patterns:
        # Simple text similarity check (could be enhanced with more sophisticated matching)
        pattern_embedding = embedding_service.encode_single(pattern["clause_pattern"])
        similarity = embedding_service.get_similarity(
            clause_embedding, pattern_embedding
        )

        if similarity >= similarity_threshold:
            match = pattern.copy()
            match["similarity"] = similarity
            matches.append(match)

    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x["similarity"], reverse=True)

    return matches


def get_legal_sources(
    db: Session, source_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get list of legal sources, optionally filtered by type.

    Args:
        db: Database session
        source_type: Filter by source type ('law', 'regulation', 'case_law', etc.)

    Returns:
        List of legal sources
    """
    query = db.query(LegalSource)

    if source_type:
        query = query.filter(LegalSource.source_type == source_type)

    sources = query.all()

    return [
        {
            "id": source.id,
            "source_type": source.source_type,
            "title": source.title,
            "jurisdiction": source.jurisdiction,
            "publisher": source.publisher,
            "source_url": source.source_url,
            "retrieved_at": (
                source.retrieved_at.isoformat() if source.retrieved_at else None
            ),
            "license_note": source.license_note,
        }
        for source in sources
    ]


def get_legal_documents(
    db: Session,
    source_id: Optional[int] = None,
    category: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Get list of legal documents, optionally filtered.

    Args:
        db: Database session
        source_id: Filter by source ID
        category: Filter by category
        limit: Maximum number of results

    Returns:
        List of legal documents
    """
    query = db.query(LegalDocument).join(LegalSource)

    if source_id:
        query = query.filter(LegalDocument.source_id == source_id)

    if category:
        query = query.filter(LegalDocument.category == category)

    documents = query.limit(limit).all()

    return [
        {
            "id": doc.id,
            "source_id": doc.source_id,
            "citation": doc.citation,
            "title": doc.title,
            "category": doc.category,
            "summary": doc.summary,
            "source_title": doc.source.title if doc.source else None,
            "source_type": doc.source.source_type if doc.source else None,
        }
        for doc in documents
    ]
