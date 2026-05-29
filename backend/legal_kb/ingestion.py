"""
Ingestion module for legal knowledge base.
Handles loading seed data and generating embeddings.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from models.legal_kb import LegalSource, LegalDocument, LegalChunk, InvalidClausePattern
from legal_kb.embeddings import embedding_service
from legal_kb.seed_data import (
    get_seed_sources,
    get_seed_documents,
    get_seed_invalid_clauses,
    get_seed_bgh_rulings,
)

logger = logging.getLogger(__name__)


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

        # Create new source.
        # Note: A 'content_hash' field was previously referenced in this code
        # for change detection, but the column was never added to the model.
        # The feature is currently unused, so we omit it.
        source = LegalSource(
            source_type=source_data["source_type"],
            title=source_data["title"],
            jurisdiction=source_data["jurisdiction"],
            publisher=source_data.get("publisher"),
            source_url=source_data.get("source_url"),
            license_note=source_data.get("license_note"),
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
            keywords=doc_data.get("keywords"),
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
    Ingest seed invalid clause patterns and generate structured embeddings for them.
    Each pattern gets an embedding from a combined description string for vector search.

    Returns:
        List of created invalid clause IDs
    """
    clauses_data = get_seed_invalid_clauses()
    clause_ids = []

    # Look up the invalid clause source dynamically from seed data
    invalid_clause_source_title = _lookup_source_title_by_type("invalid_clause")
    if not invalid_clause_source_title:
        logger.warning(
            "No invalid_clause source found in seed data, skipping invalid clauses"
        )
        return clause_ids

    source_id = source_ids.get(invalid_clause_source_title)
    if not source_id:
        logger.warning(
            f"Invalid clause source '{invalid_clause_source_title}' not found in DB, skipping invalid clauses"
        )
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

        # Map recommended_alternative to recommended_response if present
        recommended_response = clause_data.get(
            "recommended_response"
        ) or clause_data.get("recommended_alternative")

        # Build a rich text representation for embedding
        embedding_text = (
            f"Topic: {clause_data['topic']}. "
            f"Pattern: {clause_data['clause_pattern']}. "
            f"Why invalid: {clause_data['why_invalid']}. "
            f"Legal basis: {clause_data.get('legal_basis', '')}. "
            f"Example: {clause_data.get('example_text', '')}. "
            f"BGB citation: {clause_data.get('bgb_citation', '')}. "
            f"BGB text: {clause_data.get('bgb_text_excerpt', '')}."
        )

        # Generate embedding from the rich text
        embedding = embedding_service.encode_single(embedding_text)

        # Create new invalid clause pattern with pre-computed embedding
        clause = InvalidClausePattern(
            topic=clause_data["topic"],
            clause_pattern=clause_data["clause_pattern"],
            why_invalid=clause_data["why_invalid"],
            legal_basis=clause_data.get("legal_basis"),
            risk_level=clause_data["risk_level"],
            example_text=clause_data.get("example_text"),
            recommended_response=recommended_response,
            source_document_id=None,  # Could link to specific documents later
            embedding=embedding,  # Store pre-computed embedding for vector search
            bgb_citation=clause_data.get("bgb_citation"),
            bgb_text_excerpt=clause_data.get("bgb_text_excerpt"),
        )

        db.add(clause)
        db.flush()
        clause_ids.append(clause.id)
        logger.info(
            f"Created invalid clause pattern with embedding: {clause.topic} - {clause.clause_pattern[:50]}..."
        )

    db.commit()
    return clause_ids


def _lookup_source_title_by_type(source_type: str) -> Optional[str]:
    """Look up a source title from seed data by its source_type."""
    from legal_kb.seed_data import get_seed_sources

    seed_sources = get_seed_sources()
    for src in seed_sources:
        if src["source_type"] == source_type:
            return src["title"]
    return None


def ingest_seed_bgh_rulings(db: Session, source_ids: Dict[str, int]) -> List[int]:
    """
    Ingest landmark BGH rulings as legal documents under the BGH case_law source.

    Returns:
        List of created document IDs
    """
    rulings_data = get_seed_bgh_rulings()
    ruling_ids = []

    # Look up the BGH source dynamically from seed data
    bgh_source_title = _lookup_source_title_by_type("case_law")
    if not bgh_source_title:
        logger.warning("No case_law source found in seed data, skipping BGH rulings")
        return ruling_ids

    source_id = source_ids.get(bgh_source_title)
    if not source_id:
        logger.warning(
            f"BGH source '{bgh_source_title}' not found in DB, skipping BGH rulings"
        )
        return ruling_ids

    for ruling in rulings_data:
        citation = ruling["case"]

        # Check if ruling already exists
        existing = (
            db.query(LegalDocument)
            .filter(
                LegalDocument.source_id == source_id,
                LegalDocument.citation == citation,
            )
            .first()
        )

        if existing:
            ruling_ids.append(existing.id)
            continue

        # Format title and text
        title = f"{citation} - {ruling['topic']}"
        text = f"{citation} ({ruling['year']}): {ruling['summary']}"

        document = LegalDocument(
            source_id=source_id,
            citation=citation,
            title=title,
            category="case_law",
            text=text,
            summary=ruling["summary"],
            keywords=[f"year:{ruling['year']}", ruling["topic"]],
        )

        db.add(document)
        db.flush()

        # Create embedding for the ruling
        chunks = chunk_text(text)
        for i, chunk_text_content in enumerate(chunks):
            embedding = embedding_service.encode_single(chunk_text_content)
            chunk = LegalChunk(
                document_id=document.id,
                chunk_index=i,
                text=chunk_text_content,
                embedding=embedding,
                token_count=len(chunk_text_content.split()),
            )
            db.add(chunk)

        ruling_ids.append(document.id)
        logger.info(f"Created BGH ruling document: {citation}")

    db.commit()
    return ruling_ids


def clear_legal_knowledge_base(db: Session) -> Dict[str, int]:
    """
    Delete all legal knowledge base seed data from the database.

    Deletes in the correct order to respect foreign key constraints:
    1. InvalidClausePattern (no FKs to other seed tables)
    2. LegalChunk (FK to LegalDocument)
    3. LegalDocument (FK to LegalSource)
    4. LegalSource

    Returns:
        Dict with counts of deleted records per table
    """
    from sqlalchemy import text as sa_text

    logger.info("Clearing legal knowledge base...")

    # Count before deletion
    invalid_clause_count = db.query(InvalidClausePattern).count()
    chunk_count = db.query(LegalChunk).count()
    document_count = db.query(LegalDocument).count()
    source_count = db.query(LegalSource).count()

    # Delete in order: children first, then parents
    db.query(InvalidClausePattern).delete()
    db.query(LegalChunk).delete()
    db.query(LegalDocument).delete()
    db.query(LegalSource).delete()
    db.commit()

    logger.info(
        f"Cleared {invalid_clause_count} invalid clauses, {chunk_count} chunks, "
        f"{document_count} documents, {source_count} sources"
    )

    return {
        "invalid_clauses_deleted": invalid_clause_count,
        "chunks_deleted": chunk_count,
        "documents_deleted": document_count,
        "sources_deleted": source_count,
    }


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
        "total_embeddings": chunks_count + clauses_count,
    }
