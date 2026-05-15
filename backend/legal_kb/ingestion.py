"""
Ingestion module for legal knowledge base.
Handles loading seed data and generating embeddings.
"""

import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from models.legal_kb import LegalSource, LegalDocument, LegalChunk, InvalidClausePattern
from legal_kb.embeddings import embedding_service
from legal_kb.seed_data import (
    get_seed_sources,
    get_seed_documents,
    get_seed_invalid_clauses,
)

logger = logging.getLogger(__name__)


def calculate_content_hash(text: str) -> str:
    """Calculate SHA256 hash of text content for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If we're not at the end, try to find a good break point
        if end < len(text):
            # Look for sentence endings within the last 100 chars
            break_chars = [". ", "! ", "? ", "\n"]
            break_pos = -1

            for char in break_chars:
                pos = text.rfind(char, start, end)
                if pos > break_pos:
                    break_pos = pos + len(char)

            if break_pos > start + chunk_size * 0.7:  # Good break point found
                end = break_pos
            else:
                # Fall back to word boundary
                space_pos = text.rfind(" ", start, end)
                if space_pos > start + chunk_size * 0.5:
                    end = space_pos + 1

        chunk = text[start:end].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)

        # Move start position with overlap
        start = max(start + 1, end - overlap)

    return chunks


def ingest_seed_sources(db: Session) -> Dict[str, int]:
    """
    Ingest seed legal sources into database.

    Returns:
        Dict mapping source titles to their IDs
    """
    sources_data = get_seed_sources()
    source_ids = {}

    for source_data in sources_data:
        # Check if source already exists
        existing = (
            db.query(LegalSource)
            .filter(LegalSource.title == source_data["title"])
            .first()
        )

        if existing:
            source_ids[source_data["title"]] = existing.id
            continue

        # Create new source
        source = LegalSource(
            source_type=source_data["source_type"],
            title=source_data["title"],
            jurisdiction=source_data["jurisdiction"],
            publisher=source_data.get("publisher"),
            source_url=source_data.get("source_url"),
            license_note=source_data.get("license_note"),
            content_hash=calculate_content_hash(source_data["title"]),
        )

        db.add(source)
        db.flush()  # Get the ID
        source_ids[source_data["title"]] = source.id
        logger.info(f"Created legal source: {source.title}")

    db.commit()
    return source_ids


def ingest_seed_documents(db: Session, source_ids: Dict[str, int]) -> List[int]:
    """
    Ingest seed legal documents and generate embeddings.

    Returns:
        List of created document IDs
    """
    documents_data = get_seed_documents()
    document_ids = []

    for doc_data in documents_data:
        source_title = doc_data["source_title"]
        if source_title not in source_ids:
            logger.warning(f"Source not found for document: {source_title}")
            continue

        source_id = source_ids[source_title]

        # Check if document already exists
        existing = (
            db.query(LegalDocument)
            .filter(
                LegalDocument.source_id == source_id,
                LegalDocument.citation == doc_data.get("citation"),
            )
            .first()
        )

        if existing:
            document_ids.append(existing.id)
            continue

        # Create new document
        document = LegalDocument(
            source_id=source_id,
            citation=doc_data.get("citation"),
            title=doc_data["title"],
            category=doc_data.get("category"),
            text=doc_data["text"],
            summary=doc_data.get("summary"),
            metadata_json=doc_data.get("metadata_json", {}),
        )

        db.add(document)
        db.flush()  # Get the ID

        # Chunk the document and create embeddings
        chunks = chunk_text(doc_data["text"])
        for i, chunk_text_content in enumerate(chunks):
            # Generate embedding
            embedding = embedding_service.encode_single(chunk_text_content)

            chunk = LegalChunk(
                document_id=document.id,
                chunk_index=i,
                text=chunk_text_content,
                embedding=embedding,
                token_count=len(chunk_text_content.split()),  # Rough token count
            )

            db.add(chunk)

        document_ids.append(document.id)
        logger.info(
            f"Created legal document with {len(chunks)} chunks: {document.title}"
        )

    db.commit()
    return document_ids


def ingest_seed_invalid_clauses(db: Session, source_ids: Dict[str, int]) -> List[int]:
    """
    Ingest seed invalid clause patterns.

    Returns:
        List of created invalid clause IDs
    """
    clauses_data = get_seed_invalid_clauses()
    clause_ids = []

    # Get the invalid clause source
    invalid_clause_source_title = "Häufig unwirksame Klauseln in Mietverträgen"
    source_id = source_ids.get(invalid_clause_source_title)

    if not source_id:
        logger.warning("Invalid clause source not found, skipping invalid clauses")
        return clause_ids

    for clause_data in clauses_data:
        # Check if clause already exists
        existing = (
            db.query(InvalidClausePattern)
            .filter(
                InvalidClausePattern.topic == clause_data["topic"],
                InvalidClausePattern.clause_pattern == clause_data["clause_pattern"],
            )
            .first()
        )

        if existing:
            clause_ids.append(existing.id)
            continue

        # Create new invalid clause pattern
        clause = InvalidClausePattern(
            topic=clause_data["topic"],
            clause_pattern=clause_data["clause_pattern"],
            why_invalid=clause_data["why_invalid"],
            legal_basis=clause_data.get("legal_basis"),
            risk_level=clause_data["risk_level"],
            example_text=clause_data.get("example_text"),
            recommended_response=clause_data.get("recommended_response"),
            source_document_id=None,  # Could link to specific documents later
        )

        db.add(clause)
        db.flush()
        clause_ids.append(clause.id)
        logger.info(
            f"Created invalid clause pattern: {clause.topic} - {clause.clause_pattern[:50]}..."
        )

    db.commit()
    return clause_ids


def seed_legal_knowledge_base(db: Session) -> Dict[str, Any]:
    """
    Seed the entire legal knowledge base with initial data.

    Returns:
        Summary of what was created
    """
    logger.info("Starting legal knowledge base seeding...")

    # Ingest sources
    source_ids = ingest_seed_sources(db)
    logger.info(f"Processed {len(source_ids)} legal sources")

    # Ingest documents
    document_ids = ingest_seed_documents(db, source_ids)
    logger.info(f"Processed {len(document_ids)} legal documents")

    # Ingest invalid clause patterns
    clause_ids = ingest_seed_invalid_clauses(db, source_ids)
    logger.info(f"Processed {len(clause_ids)} invalid clause patterns")

    summary = {
        "sources_created": len(source_ids),
        "documents_created": len(document_ids),
        "clauses_created": len(clause_ids),
        "completed_at": datetime.utcnow().isoformat(),
    }

    logger.info(f"Legal knowledge base seeding completed: {summary}")
    return summary


def get_kb_stats(db: Session) -> Dict[str, Any]:
    """Get statistics about the legal knowledge base."""
    sources_count = db.query(LegalSource).count()
    documents_count = db.query(LegalDocument).count()
    chunks_count = db.query(LegalChunk).count()
    clauses_count = db.query(InvalidClausePattern).count()

    return {
        "sources": sources_count,
        "documents": documents_count,
        "chunks": chunks_count,
        "invalid_clauses": clauses_count,
        "total_embeddings": chunks_count,
    }
