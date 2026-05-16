"""
Pydantic schemas for the legal knowledge base API.
Defines request/response models for legal KB endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkResult(BaseModel):
    """A document chunk from vector search results."""

    chunk_id: int = Field(..., description="Chunk ID")
    chunk_index: int = Field(..., description="Position within document")
    text: str = Field(..., description="Chunk text content")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    token_count: Optional[int] = Field(None, description="Approximate token count")


class DocumentResult(BaseModel):
    """A document from search results, grouped with its chunks."""

    document_id: int = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    citation: Optional[str] = Field(
        None, description="Legal citation (e.g., BGB § 551)"
    )
    category: Optional[str] = Field(None, description="Document category")
    summary: Optional[str] = Field(None, description="Document summary")
    source_title: Optional[str] = Field(None, description="Source title")
    source_type: Optional[str] = Field(None, description="Source type")
    publisher: Optional[str] = Field(None, description="Publisher name")
    chunks: List[ChunkResult] = Field(
        default_factory=list, description="Matching chunks"
    )


class SearchResponse(BaseModel):
    """Response model for legal knowledge base search."""

    query: str = Field(..., description="The search query")
    total_results: int = Field(..., description="Total number of results found")
    documents: List[DocumentResult] = Field(
        default_factory=list, description="Matching documents grouped by source"
    )
    search_parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Search parameters used"
    )


class InvalidClausePattern(BaseModel):
    """A known invalid clause pattern."""

    id: int = Field(..., description="Pattern ID")
    topic: str = Field(..., description="Topic (e.g., Kaution, Kündigung)")
    clause_pattern: str = Field(..., description="Pattern or example text")
    why_invalid: str = Field(..., description="Explanation of invalidity")
    legal_basis: Optional[str] = Field(None, description="Legal basis citation")
    risk_level: str = Field(..., description="Risk level: high, medium, low")
    example_text: Optional[str] = Field(None, description="Concrete example")
    recommended_response: Optional[str] = Field(
        None, description="How tenant should respond"
    )


class InvalidClauseCheckResponse(BaseModel):
    """Response model for checking a clause against invalid patterns."""

    matches: List[Dict[str, Any]] = Field(
        default_factory=list, description="Matching invalid clause patterns"
    )


class SeedResponse(BaseModel):
    """Response model for seeding the legal knowledge base."""

    message: str = Field(..., description="Status message")
    sources_created: int = Field(..., description="Number of sources created")
    documents_created: int = Field(..., description="Number of documents created")
    invalid_clauses_created: int = Field(
        ..., description="Number of invalid clauses created"
    )
    embeddings_created: int = Field(..., description="Number of embeddings generated")


class KBStatsResponse(BaseModel):
    """Statistics about the legal knowledge base."""

    sources: int = Field(..., description="Number of legal sources")
    documents: int = Field(..., description="Number of legal documents")
    chunks: int = Field(..., description="Number of document chunks")
    invalid_clauses: int = Field(..., description="Number of invalid clause patterns")
    total_embeddings: int = Field(..., description="Total embeddings stored")
