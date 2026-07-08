"""
Integration tests for the contracts router.
Tests endpoint response structure, error handling, and service integration.
"""

from unittest.mock import MagicMock, patch
from io import BytesIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.dependencies import get_db, get_nlp_model
from core.auth import get_current_principal
from routers.contracts import router as contracts_router, get_current_principal_for_analyze
from schemas.contract import (
    ContractAnalysisResponse,
    ContractAnalysisResult,
    ContractIssue,
    NamedEntity,
)
from tests.conftest import MockDoc

# ============================================================
# Helper: Create a test app with mocked dependencies
# ============================================================


def create_test_app(mock_db, mock_nlp):
    """Create a FastAPI test app with overridden dependencies (including auth)."""
    from core.auth import Principal

    app = FastAPI()
    app.include_router(contracts_router)

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_nlp_model] = lambda: mock_nlp

    # Always provide a valid admin principal for existing tests.
    # This keeps test churn minimal while still exercising the auth dependency.
    test_admin = Principal(role="admin", token="test-admin-key", is_admin=True)
    app.dependency_overrides[get_current_principal] = lambda: test_admin
    app.dependency_overrides[get_current_principal_for_analyze] = lambda: test_admin

    return app


# ============================================================
# Tests
# ============================================================


class TestAnalyzeContractEndpoint:
    def test_successful_analysis(self, mock_db_session, mock_nlp_model):
        """Should return 200 with analysis response for valid PDF."""
        mock_nlp = mock_nlp_model
        app = create_test_app(mock_db_session, mock_nlp)

        # Mock the analyze_contract service to return a proper response
        mock_response = ContractAnalysisResponse(
            filename="test.pdf",
            contract_id=1,
            processing_method="text_extraction",
            ocr_used="none",
            processing_time_seconds=2,
            analysis=ContractAnalysisResult(
                word_count=150,
                sentences=12,
                key_terms=["Miete", "Kaution"],
                entities=[NamedEntity(text="Berlin", label="GPE")],
                issues=[
                    ContractIssue(
                        description="Kaution zu hoch (Risk: high)",
                        risk_level="high",
                        legal_basis="BGB § 551",
                    )
                ],
            ),
        )

        with patch(
            "routers.contracts.analyze_contract",
            return_value=(mock_response, 2.0),
        ):
            client = TestClient(app)
            response = client.post(
                "/contracts/analyze",
                files={
                    "file": ("test.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["contract_id"] == 1
        assert data["processing_method"] == "text_extraction"
        assert data["ocr_used"] == "none"
        assert data["processing_time_seconds"] == 2
        assert data["analysis"]["word_count"] == 150
        assert data["analysis"]["sentences"] == 12
        assert "Miete" in data["analysis"]["key_terms"]
        assert len(data["analysis"]["issues"]) == 1
        assert data["analysis"]["issues"][0]["risk_level"] == "high"

    def test_rejects_non_pdf_file(self, mock_db_session, mock_nlp_model):
        """Should return 400 for non-PDF uploads."""
        app = create_test_app(mock_db_session, mock_nlp_model)
        client = TestClient(app)

        response = client.post(
            "/contracts/analyze",
            files={"file": ("test.txt", BytesIO(b"plain text"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]

    def test_handles_internal_error(self, mock_db_session, mock_nlp_model):
        """Should return 500 on unexpected service errors."""
        mock_nlp = mock_nlp_model
        app = create_test_app(mock_db_session, mock_nlp)

        with patch(
            "routers.contracts.analyze_contract",
            side_effect=ValueError("Unexpected DB error"),
        ):
            client = TestClient(app)
            response = client.post(
                "/contracts/analyze",
                files={
                    "file": ("test.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")
                },
            )

        assert response.status_code == 500
        assert (
            "internal" in response.json()["detail"].lower()
            or "error" in response.json()["detail"].lower()
        )
