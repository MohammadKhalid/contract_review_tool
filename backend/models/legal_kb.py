"""
Models for legal knowledge base.
Defines database models for storing legal sources, documents, and clause patterns.
"""

from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSON as PG_JSON
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database.connection import Base


class LegalSource(Base):
    """Represents a legal source (e.g., BGB, BGH rulings, regulations)."""

    __tablename__ = "legal_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(
        String, nullable=False
    )  # 'law', 'case_law', 'regulation', etc.
    title = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=True)  # e.g., 'DE'
    publisher = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    retrieved_at = Column(String, nullable=True)
    license_note = Column(String, nullable=True)

    # Relationships
    documents = relationship("LegalDocument", back_populates="source")


class LegalDocument(Base):
    """Represents a specific legal document (e.g., BGB § 535)."""

    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("legal_sources.id"), nullable=False)
    citation = Column(String, nullable=False)  # e.g., 'BGB § 535'
    title = Column(String, nullable=True)  # Short title/description
    category = Column(String, nullable=True)  # e.g., 'deposit', 'termination'
    summary = Column(String, nullable=True)
    text = Column(Text, nullable=False)  # Full legal text
    keywords = Column(PG_JSON, nullable=True)  # List of keywords

    # Relationships
    source = relationship("LegalSource", back_populates="documents")
    chunks = relationship("LegalChunk", back_populates="document")


class LegalChunk(Base):
    """Represents a chunk of a legal document with its embedding."""

    __tablename__ = "legal_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    text = Column(Text, nullable=False)  # Chunk text
    embedding = Column(
        Vector(384)
    )  # 384 dimensions for paraphrase-multilingual-MiniLM-L12-v2
    token_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # Additional chunk metadata

    # Relationships
    document = relationship("LegalDocument", back_populates="chunks")

    # Index for vector similarity search
    __table_args__ = (
        Index("legal_chunks_embedding_idx", embedding, postgresql_using="ivfflat"),
    )


class InvalidClausePattern(Base):
    """Stores common invalid/unfair clause examples as structured rules"""

    __tablename__ = "invalid_clause_patterns"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(
        String, nullable=False
    )  # e.g. 'Kaution', 'Schönheitsreparaturen', 'Kündigung'
    clause_pattern = Column(Text, nullable=False)  # Pattern or example text
    why_invalid = Column(Text, nullable=False)  # Explanation of invalidity
    legal_basis = Column(String, nullable=True)  # Citation to supporting law/ruling
    risk_level = Column(String, nullable=False)  # 'high', 'medium', 'low'
    example_text = Column(Text, nullable=True)  # Concrete example
    recommended_response = Column(Text, nullable=True)  # How tenant should respond
    source_document_id = Column(
        Integer, ForeignKey("legal_documents.id"), nullable=True
    )
    embedding = Column(
        Vector(384), nullable=True
    )  # Pre-computed embedding for vector search
    bgb_citation = Column(String, nullable=True)  # Exact BGB paragraph citation
    bgb_text_excerpt = Column(Text, nullable=True)  # Exact BGB text excerpt

    # Relationships
    source_document = relationship("LegalDocument")

    # Index for vector similarity search on invalid clause patterns
    __table_args__ = (
        Index(
            "invalid_clause_embedding_idx",
            embedding,
            postgresql_using="ivfflat",
        ),
    )
