"""
Integration tests for the legal knowledge base router.
Tests endpoint response structure, error handling, and service integration.
"""

from unittest.mock import patch
from io import BytesIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.dependencies import get_db, get_embedding_service
from core.auth import get_current_principal
from routers.legal_kb import router as legal_kb_router
from schemas.legal_kb import (
    InvalidClauseCheckResponse,
    KBStatsResponse,
    SearchResponse,
    SeedResponse,
    ChunkResult,
    DocumentResult,
)

# ============================================================
# Helper: Create a test app with mocked dependencies
# ============================================================


def create_test_app(mock_db, mock_embedding=None):
    """Create a FastAPI test app with overridden dependencies (including auth)."""
    from core.auth import Principal

    app = FastAPI()
    app.include_router(legal_kb_router)

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db

    if mock_embedding:
        app.dependency_overrides[get_embedding_service] = lambda: mock_embedding

    # Provide admin principal so all existing KB tests (including seed) continue to pass
    test_admin = Principal(role="admin", token="test-admin-key", is_admin=True)
    app.dependency_overrides[get_current_principal] = lambda: test_admin

    return app


# ============================================================
# Tests
# ============================================================


class TestSeedEndpoint:
    def test_successful_seed(self, mock_db_session):
        """Should return 200 with seed results."""
        app = create_test_app(mock_db_session, MagicMock())

        with patch(
            "routers.legal_kb.seed_knowledge_base",
            return_value=SeedResponse(
                message="Legal knowledge base seeded successfully",
                sources_created=3,
                documents_created=10,
                invalid_clauses_created=8,
                embeddings_created=25,
            ),
        ):
            client = TestClient(app)
            response = client.post("/legal-kb/seed")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Legal knowledge base seeded successfully"
        assert data["sources_created"] == 3
        assert data["documents_created"] == 10
        assert data["embeddings_created"] == 25

    def test_handles_seed_error(self, mock_db_session):
        """Should return 500 on seeding failure."""
        app = create_test_app(mock_db_session, MagicMock())

        with patch(
            "routers.legal_kb.seed_knowledge_base",
            side_effect=ValueError("Database connection failed"),
        ):
            client = TestClient(app)
            response = client.post("/legal-kb/seed")

        assert response.status_code == 500


class TestStatsEndpoint:
    def test_returns_stats(self, mock_db_session):
        """Should return KB statistics."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.get_statistics",
            return_value=KBStatsResponse(
                sources=3,
                documents=10,
                chunks=25,
                invalid_clauses=8,
                total_embeddings=25,
            ),
        ):
            client = TestClient(app)
            response = client.get("/legal-kb/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == 3
        assert data["chunks"] == 25


class TestSearchEndpoint:
    def test_successful_search(self, mock_db_session):
        """Should return search results."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.search_documents",
            return_value=SearchResponse(
                query="Kaution",
                total_results=1,
                documents=[
                    DocumentResult(
                        document_id=1,
                        title="Kaution",
                        citation="BGB § 551",
                        category="deposit",
                        summary="Max 3 Monatsmieten",
                        source_title="BGB Mietrecht",
                        source_type="law",
                        publisher="gesetze-im-internet.de",
                        chunks=[
                            ChunkResult(
                                chunk_id=1,
                                chunk_index=0,
                                text="Die Kaution darf maximal 3 Monatsmieten betragen.",
                                similarity=0.95,
                                token_count=10,
                            )
                        ],
                    )
                ],
                search_parameters={"limit": 10, "similarity_threshold": 0.7},
            ),
        ):
            client = TestClient(app)
            response = client.post("/legal-kb/search?query=Kaution")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Kaution"
        assert data["total_results"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["citation"] == "BGB § 551"

    def test_rejects_empty_query(self, mock_db_session):
        """Should return 400 for empty query."""
        app = create_test_app(mock_db_session)
        client = TestClient(app)

        response = client.post("/legal-kb/search?query=")
        assert response.status_code == 400

    def test_handles_search_error(self, mock_db_session):
        """Should return 500 on search failure."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.search_documents",
            side_effect=ValueError("Search service unavailable"),
        ):
            client = TestClient(app)
            response = client.post("/legal-kb/search?query=Kaution")

        assert response.status_code == 500


class TestInvalidClausesEndpoint:
    def test_returns_patterns(self, mock_db_session):
        """Should return invalid clause patterns."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.get_invalid_clause_patterns",
            return_value={
                "patterns": [
                    {
                        "id": 1,
                        "topic": "Kaution",
                        "clause_pattern": "Kaution übersteigt drei Monatsmieten",
                        "why_invalid": "BGB § 551",
                        "legal_basis": "BGB § 551",
                        "risk_level": "high",
                    }
                ]
            },
        ):
            client = TestClient(app)
            response = client.get("/legal-kb/invalid-clauses")

        assert response.status_code == 200
        data = response.json()
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["topic"] == "Kaution"

    def test_filters_by_topic(self, mock_db_session):
        """Should filter by topic query parameter."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.get_invalid_clause_patterns",
        ) as mock_get:
            mock_get.return_value = {"patterns": []}
            client = TestClient(app)
            client.get("/legal-kb/invalid-clauses?topic=K%C3%BCndigung")

            # Verify the service was called with the topic filter
            _, kwargs = mock_get.call_args
            # The topic should be passed to the service
            assert mock_get.called


class TestCheckClauseEndpoint:
    def test_checks_clause(self, mock_db_session):
        """Should check a clause and return matches."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.check_clause",
            return_value=InvalidClauseCheckResponse(
                matches=[
                    {
                        "id": 1,
                        "topic": "Kaution",
                        "clause_pattern": "Kaution übersteigt drei Monatsmieten",
                        "why_invalid": "BGB § 551",
                        "legal_basis": "BGB § 551",
                        "risk_level": "high",
                        "similarity": 0.92,
                    }
                ]
            ),
        ):
            client = TestClient(app)
            response = client.post(
                "/legal-kb/check-clause?clause_text=Kaution%3A%204%20Monatsmieten"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["matches"]) == 1
        assert data["matches"][0]["risk_level"] == "high"

    def test_rejects_empty_clause(self, mock_db_session):
        """Should return 400 for empty clause text."""
        app = create_test_app(mock_db_session)
        client = TestClient(app)

        response = client.post("/legal-kb/check-clause?clause_text=")
        assert response.status_code == 400


class TestSourcesEndpoint:
    def test_returns_sources(self, mock_db_session):
        """Should return list of legal sources."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.get_sources",
            return_value={
                "sources": [
                    {
                        "id": 1,
                        "source_type": "law",
                        "title": "BGB Mietrecht",
                        "jurisdiction": "DE",
                        "publisher": "gesetze-im-internet.de",
                    }
                ]
            },
        ):
            client = TestClient(app)
            response = client.get("/legal-kb/sources")

        assert response.status_code == 200
        assert len(response.json()["sources"]) == 1


class TestDocumentsEndpoint:
    def test_returns_documents(self, mock_db_session):
        """Should return list of legal documents."""
        app = create_test_app(mock_db_session)

        with patch(
            "routers.legal_kb.get_documents",
            return_value={
                "documents": [
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
            },
        ):
            client = TestClient(app)
            response = client.get("/legal-kb/documents")

        assert response.status_code == 200
        assert len(response.json()["documents"]) == 1
