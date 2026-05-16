"""
Pydantic schemas for contract upload and analysis.
Defines request/response models for the contracts API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NamedEntity(BaseModel):
    """A named entity extracted from text."""

    text: str = Field(..., description="The entity text")
    label: str = Field(..., description="The entity label (e.g., PERSON, ORG, MONEY)")


class ContractIssue(BaseModel):
    """A potential legal issue found in a contract clause."""

    description: str = Field(..., description="Description of the issue")
    risk_level: Optional[str] = Field(None, description="Risk level: high, medium, low")
    legal_basis: Optional[str] = Field(None, description="Legal basis citation")
    clause_snippet: Optional[str] = Field(
        None, description="The clause text that triggered the issue"
    )
    similarity: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Similarity score to known pattern"
    )


class ContractAnalysisResult(BaseModel):
    """Results of a contract analysis."""

    word_count: int = Field(..., description="Total word count")
    sentences: int = Field(..., alias="sentences", description="Total sentence count")
    key_terms: List[str] = Field(
        default_factory=list, description="Found key legal terms"
    )
    entities: List[NamedEntity] = Field(
        default_factory=list, description="Extracted named entities"
    )
    issues: List[ContractIssue] = Field(
        default_factory=list, description="Potential legal issues"
    )


class ContractAnalysisResponse(BaseModel):
    """Response model for contract analysis endpoint."""

    filename: str = Field(..., description="Original filename")
    contract_id: int = Field(..., description="Database contract ID")
    processing_method: str = Field(
        ..., description="How text was extracted: text_extraction, ocr, ocr_fallback"
    )
    ocr_used: str = Field(..., description="OCR status: none, primary, fallback")
    processing_time_seconds: int = Field(
        ..., description="Time taken to process in seconds"
    )
    analysis: ContractAnalysisResult


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")
    status_code: Optional[int] = Field(None, description="HTTP status code")
