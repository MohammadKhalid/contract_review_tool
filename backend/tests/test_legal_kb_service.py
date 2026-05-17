"""
Unit tests for the legal knowledge base service.
Tests service functions that wrap ingestion and retrieval modules.
"""

from unittest.mock import MagicMock, patch
from typing import Any, Dict, List

import pytest

from services.legal_kb_service import (
    get_statistics,
    get_invalid_clause_patterns,
    check_clause,
    get_sources,
    get_documents,
)
from core.exceptions import NotFoundException
from schemas.legal_kb import (
    InvalidClauseCheckResponse,
    KBStatsResponse,
)

# ============================================================
# Tests for get_statistics
# ============================================================


class TestGetStatistics:
    def test_returns_stats_response(self, mock_db_session):
        """Should return a KBStatsResponse object."""
        mock_db_session.query.return_value.count.return_value = 5

        with patch(
            "services.legal_kb_service.get_kb_stats",
            return_value={
                "sources": 3,
                "documents": 10,
                "chunks": 25,
                "invalid_clauses": 8,
                "total_embeddings": 25,
            },
        ):
            stats = get_statistics(mock_db_session)
            assert isinstance(stats, KBStatsResponse)
            assert stats.sources == 3
            assert stats.documents == 10
            assert stats.chunks == 25
            assert stats.invalid_clauses == 8
            assert stats.total_embeddings == 25

    def test_zero_counts(self, mock_db_session):
        """Should handle empty database gracefully."""
        with patch(
            "services.legal_kb_service.get_kb_stats",
            return_value={
                "sources": 0,
                "documents": 0,
                "chunks": 0,
                "invalid_clauses": 0,
                "total_embeddings": 0,
            },
        ):
            stats = get_statistics(mock_db_session)
            assert stats.sources == 0
            assert stats.total_embeddings == 0


# ============================================================
# Tests for get_invalid_clause_patterns
# ============================================================


class TestGetInvalidClausePatterns:
    def test_returns_all_patterns(self, mock_db_session):
        """Should return all patterns when no filters applied."""
        mock_patterns = [
            {
                "id": 1,
                "topic": "Kaution",
                "clause_pattern": "Kaution übersteigt drei Monatsmieten",
                "why_invalid": "BGB § 551",
                "legal_basis": "BGB § 551",
                "risk_level": "high",
                "example_text": "Kaution: 4 Monatsmieten",
                "recommended_response": "Reduzieren",
            },
            {
                "id": 2,
                "topic": "Kündigung",
                "clause_pattern": "Verkürzte Kündigungsfrist",
                "why_invalid": "BGB § 573c",
                "legal_basis": "BGB § 573c",
                "risk_level": "high",
                "example_text": "1 Monat Kündigungsfrist",
                "recommended_response": "Auf 3 Monate ändern",
            },
        ]

        with patch(
            "services.legal_kb_service.retrieval_get_patterns",
            return_value=mock_patterns,
        ):
            result = get_invalid_clause_patterns(mock_db_session)
            assert "patterns" in result
            assert len(result["patterns"]) == 2

    def test_filters_by_topic(self, mock_db_session):
        """Should filter patterns by topic."""
        with patch(
            "services.legal_kb_service.retrieval_get_patterns",
            return_value=[
                {
                    "id": 1,
                    "topic": "Kaution",
                    "clause_pattern": "Test",
                    "why_invalid": "Test",
                    "legal_basis": "BGB",
                    "risk_level": "high",
                    "example_text": "Test",
                    "recommended_response": "Test",
                }
            ],
        ):
            result = get_invalid_clause_patterns(mock_db_session, topic="Kaution")
            assert len(result["patterns"]) == 1
            assert result["patterns"][0]["topic"] == "Kaution"

    def test_returns_empty_list_when_no_matches(self, mock_db_session):
        """Should return empty patterns list when no matches."""
        with patch(
            "services.legal_kb_service.retrieval_get_patterns",
            return_value=[],
        ):
            result = get_invalid_clause_patterns(mock_db_session, topic="NonExistent")
            assert result["patterns"] == []


# ============================================================
# Tests for check_clause
# ============================================================


class TestCheckClause:
    def test_returns_check_response(self, mock_db_session):
        """Should return an InvalidClauseCheckResponse object."""
        matches = [
            {
                "id": 1,
                "topic": "Kaution",
                "clause_pattern": "Kaution übersteigt drei Monatsmieten",
                "why_invalid": "BGB § 551 verletzt",
                "legal_basis": "BGB § 551",
                "risk_level": "high",
                "similarity": 0.92,
            }
        ]

        with patch(
            "services.legal_kb_service.retrieval_check_clause",
            return_value=matches,
        ):
            result = check_clause(mock_db_session, "Kaution: 4 Monatsmieten")
            assert isinstance(result, InvalidClauseCheckResponse)
            assert len(result.matches) == 1
            assert result.matches[0]["risk_level"] == "high"

    def test_no_matches(self, mock_db_session):
        """Should return empty matches for clean clause."""
        with patch(
            "services.legal_kb_service.retrieval_check_clause",
            return_value=[],
        ):
            result = check_clause(mock_db_session, "Die Miete beträgt 800 Euro.")
            assert result.matches == []


# ============================================================
# Tests for get_sources
# ============================================================


class TestGetSources:
    def test_returns_sources_list(self, mock_db_session):
        """Should return list of legal sources."""
        mock_sources = [
            {
                "id": 1,
                "source_type": "law",
                "title": "BGB Mietrecht",
                "jurisdiction": "DE",
                "publisher": "gesetze-im-internet.de",
                "source_url": "https://example.com",
                "retrieved_at": "2024-01-01T00:00:00",
                "license_note": "Public domain",
            }
        ]

        with patch(
            "services.legal_kb_service.retrieval_get_sources",
            return_value=mock_sources,
        ):
            result = get_sources(mock_db_session)
            assert "sources" in result
            assert len(result["sources"]) == 1
            assert result["sources"][0]["title"] == "BGB Mietrecht"

    def test_filters_by_source_type(self, mock_db_session):
        """Should filter by source_type."""
        with patch(
            "services.legal_kb_service.retrieval_get_sources",
            return_value=[
                {
                    "id": 2,
                    "source_type": "regulation",
                    "title": "BetrKV",
                    "jurisdiction": "DE",
                    "publisher": "gesetze-im-internet.de",
                    "source_url": "https://example.com",
                    "retrieved_at": None,
                    "license_note": None,
                }
            ],
        ):
            result = get_sources(mock_db_session, source_type="regulation")
            assert result["sources"][0]["source_type"] == "regulation"


# ============================================================
# Tests for get_documents
# ============================================================


class TestGetDocuments:
    def test_returns_documents_list(self, mock_db_session):
        """Should return list of legal documents."""
        mock_docs = [
            {
                "id": 1,
                "source_id": 1,
                "citation": "BGB § 551",
                "title": "Kaution",
                "category": "deposit",
                "summary": "Max 3 Monatsmieten",
                "source_title": "BGB Mietrecht",
                "source_type": "law",
            }
        ]

        with patch(
            "services.legal_kb_service.retrieval_get_documents",
            return_value=mock_docs,
        ):
            result = get_documents(mock_db_session)
            assert "documents" in result
            assert len(result["documents"]) == 1
            assert result["documents"][0]["citation"] == "BGB § 551"

    def test_filters_by_category(self, mock_db_session):
        """Should filter documents by category."""
        with patch(
            "services.legal_kb_service.retrieval_get_documents",
            return_value=[
                {
                    "id": 2,
                    "source_id": 1,
                    "citation": "BGB § 573",
                    "title": "Kündigung",
                    "category": "termination",
                    "summary": "Kündigungsfristen",
                    "source_title": "BGB Mietrecht",
                    "source_type": "law",
                }
            ],
        ):
            result = get_documents(mock_db_session, category="termination")
            assert result["documents"][0]["category"] == "termination"

    def test_raises_not_found_for_missing_source(self, mock_db_session):
        """Should raise NotFoundException when source_title doesn't exist."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(NotFoundException, match="Source not found"):
            get_documents(mock_db_session, source_title="NonExistentSource")
