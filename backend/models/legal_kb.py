from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database.connection import Base
from pgvector.sqlalchemy import Vector


class LegalSource(Base):
    """Stores metadata about legal sources (laws, regulations, case law, checklists)"""

    __tablename__ = "legal_sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(
        String, nullable=False
    )  # 'law', 'regulation', 'case_law', 'checklist', 'invalid_clause'
    title = Column(String, nullable=False)
    jurisdiction = Column(String, default="DE")  # Usually 'DE' for Germany
    publisher = Column(
        String, nullable=True
    )  # e.g. 'gesetze-im-internet', 'BGH', 'Mieterbund'
    source_url = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    effective_date = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, default=datetime.utcnow)
    license_note = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)  # For detecting changes

    # Relationships
    documents = relationship(
        "LegalDocument", back_populates="source", cascade="all, delete-orphan"
    )


class LegalDocument(Base):
    """Stores structured legal documents/sections"""

    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("legal_sources.id"), nullable=False)
    citation = Column(
        String, nullable=True
    )  # e.g. 'BGB § 551', 'BetrKV § 2', 'BGH VIII ZR ...'
    title = Column(String, nullable=False)
    category = Column(
        String, nullable=True
    )  # 'deposit', 'termination', 'operating_costs', 'agb', etc.
    text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # Additional structured metadata

    # Relationships
    source = relationship("LegalSource", back_populates="documents")
    chunks = relationship(
        "LegalChunk", back_populates="document", cascade="all, delete-orphan"
    )


class LegalChunk(Base):
    """Stores chunked text and embeddings for vector search"""

    __tablename__ = "legal_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("legal_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position within document
    text = Column(Text, nullable=False)
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

    # Relationships
    source_document = relationship("LegalDocument")
