"""
Unit tests for the contract analysis service.
Tests pure business logic functions independently from FastAPI/HTTP.
"""

from unittest.mock import MagicMock, patch
from io import BytesIO

import asyncio
import pytest

from services.contract_service import (
    validate_pdf,
    split_into_clauses,
    analyze_text_with_spacy,
    detect_legal_issues,
    save_upload_file,
)
from core.exceptions import BadRequestException, FileProcessingException
from tests.conftest import MockDoc, MockEntity, MockToken, MockSpan

# ============================================================
# Tests for validate_pdf
# ============================================================


class TestValidatePdf:
    def test_valid_pdf(self):
        """Should succeed for .pdf extension."""
        validate_pdf("contract.pdf")  # No exception expected

    def test_valid_pdf_uppercase(self):
        """Should succeed for .PDF extension."""
        validate_pdf("contract.PDF")

    def test_rejects_non_pdf(self):
        """Should raise BadRequestException for non-.pdf files."""
        with pytest.raises(BadRequestException, match="Only PDF files are supported"):
            validate_pdf("contract.txt")

    def test_rejects_empty_filename(self):
        """Should raise BadRequestException for empty filename."""
        with pytest.raises(BadRequestException, match="Only PDF files are supported"):
            validate_pdf("")

    def test_rejects_none_filename(self):
        """Should raise BadRequestException for None filename."""
        with pytest.raises(BadRequestException, match="Only PDF files are supported"):
            validate_pdf(None)

    def test_rejects_no_extension(self):
        """Should raise BadRequestException for filenames without extension."""
        with pytest.raises(BadRequestException, match="Only PDF files are supported"):
            validate_pdf("contract")


# ============================================================
# Tests for split_into_clauses
# ============================================================


class TestSplitIntoClauses:
    def test_split_by_double_newline(self, sample_contract_text):
        """Should split text by double newlines (paragraphs)."""
        doc = MockDoc(sample_contract_text)
        clauses = split_into_clauses(sample_contract_text, doc)
        # Should find multiple clauses separated by blank lines
        assert len(clauses) > 1
        # First clause should be the title
        assert "MIETVERTRAG" in clauses[0]
        # Should contain the Kaution clause
        assert any("Kaution" in c for c in clauses)

    def test_preserves_clause_order(self, sample_contract_text):
        """Should maintain original order of clauses."""
        doc = MockDoc(sample_contract_text)
        clauses = split_into_clauses(sample_contract_text, doc)
        # Check order: MIETVERTRAG comes before Kaution comes before Kündigung
        mietvertrag_idx = next(i for i, c in enumerate(clauses) if "MIETVERTRAG" in c)
        kaution_idx = next(i for i, c in enumerate(clauses) if "Kaution" in c)
        kuendigung_idx = next(i for i, c in enumerate(clauses) if "Kündigung" in c)
        assert mietvertrag_idx < kaution_idx < kuendigung_idx

    def test_fallback_to_sentences(self):
        """Should fall back to sentences if no double newlines found."""
        text = "Erster Satz. Zweiter Satz. Dritter Satz."
        doc = MockDoc(text)
        clauses = split_into_clauses(text, doc)
        assert len(clauses) == 3
        assert "Erster Satz" in clauses[0]

    def test_empty_text(self):
        """Should return empty list for empty text."""
        text = ""
        doc = MockDoc("")
        clauses = split_into_clauses(text, doc)
        assert clauses == []

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace from clauses."""
        text = "  Klausel eins  \n\n  Klausel zwei  "
        doc = MockDoc(text)
        clauses = split_into_clauses(text, doc)
        assert all(c == c.strip() for c in clauses)

    def test_removes_empty_clauses(self):
        """Should not include empty or whitespace-only clauses."""
        text = "Klausel eins\n\n   \n\nKlausel zwei"
        doc = MockDoc(text)
        clauses = split_into_clauses(text, doc)
        assert len(clauses) == 2


# ============================================================
# Tests for analyze_text_with_spacy
# ============================================================


class TestAnalyzeTextWithSpacy:
    def test_word_count(self, sample_mock_doc):
        """Should count words excluding punctuation and spaces."""
        word_count, _, _, _ = analyze_text_with_spacy(sample_mock_doc)
        assert word_count > 0
        # Each token from split() counted (minus punct)
        # The sample has many German words
        assert isinstance(word_count, int)

    def test_sentence_count(self, sample_mock_doc):
        """Should count sentences."""
        _, sentence_count, _, _ = analyze_text_with_spacy(sample_mock_doc)
        assert sentence_count > 0
        assert isinstance(sentence_count, int)

    def test_key_terms_found(self, sample_mock_doc):
        """Should find German key terms present in text."""
        _, _, key_terms, _ = analyze_text_with_spacy(sample_mock_doc)
        # "Miete", "Kaution", "Vermieter", "Mieter" should be found
        assert "Miete" in key_terms
        assert "Kaution" in key_terms
        assert "Mieter" in key_terms

    def test_key_terms_not_found(self):
        """Should return empty list when no key terms match."""
        doc = MockDoc("Dieser Text enthält keine relevanten Begriffe.")
        _, _, key_terms, _ = analyze_text_with_spacy(doc)
        assert key_terms == []

    def test_named_entities_extracted(self, sample_mock_doc):
        """Should extract named entities filtered by relevant labels."""
        _, _, _, entities = analyze_text_with_spacy(sample_mock_doc)
        assert len(entities) > 0
        # Check entity structure
        entity = entities[0]
        assert "text" in entity
        assert "label" in entity
        # Should include PERSON and GPE entities
        labels = {e["label"] for e in entities}
        assert "PERSON" in labels
        assert "GPE" in labels or "MONEY" in labels

    def test_filters_irrelevant_entity_labels(self):
        """Should exclude entities with non-contract labels."""
        doc_with_irrelevant = MockDoc("Some text")
        doc_with_irrelevant.ents = [
            MockEntity("DEUTSCHLAND", "LOC"),
            MockEntity("gestern", "DATE"),
            MockEntity("123", "CARDINAL"),  # Not in relevant set
        ]
        _, _, _, entities = analyze_text_with_spacy(doc_with_irrelevant)
        # LOC and CARDINAL are not in the relevant_labels set
        labels = {e["label"] for e in entities}
        assert "LOC" not in labels
        assert "CARDINAL" not in labels

    def test_empty_doc(self):
        """Should handle empty document gracefully."""
        doc = MockDoc("")
        word_count, sentence_count, key_terms, entities = analyze_text_with_spacy(doc)
        assert word_count == 0
        assert sentence_count == 0
        assert key_terms == []
        assert entities == []


# ============================================================
# Tests for detect_legal_issues
# ============================================================


class TestDetectLegalIssues:
    def test_no_matches(self, mock_db_session):
        """Should return empty list when no clauses match patterns."""
        with patch(
            "services.contract_service.check_clause_against_patterns",
            return_value=[],
        ):
            issues = asyncio.run(detect_legal_issues(mock_db_session, ["Clean clause."]))
            assert issues == []

    def test_detects_kaution_issue(self, mock_db_session, mock_clause_pattern_matches):
        """Should detect high-risk Kaution issue."""
        with patch(
            "services.contract_service.check_clause_against_patterns",
            return_value=[mock_clause_pattern_matches[0]],
        ):
            issues = asyncio.run(detect_legal_issues(
                mock_db_session,
                ["Der Mieter leistet eine Kaution in Höhe von vier Monatsmieten."],
            ))
            assert len(issues) == 1
            assert issues[0].risk_level == "high"
            assert "Kaution" in issues[0].description

    def test_detects_multiple_issues(
        self, mock_db_session, mock_clause_pattern_matches
    ):
        """Should detect issues from multiple clauses."""

        def mock_check(db, clause):
            if "Kaution" in clause:
                return [mock_clause_pattern_matches[0]]
            elif "Nebenkosten" in clause:
                return [mock_clause_pattern_matches[1]]
            return []

        with patch(
            "services.contract_service.check_clause_against_patterns",
            side_effect=mock_check,
        ):
            clauses = [
                "Der Mieter leistet eine Kaution in Höhe von vier Monatsmieten.",
                "Die Nebenkosten betragen pauschal 150€ pro Monat.",
            ]
            issues = asyncio.run(detect_legal_issues(mock_db_session, clauses))
            assert len(issues) == 2
            # Should be sorted by similarity (highest first)
            assert issues[0].risk_level == "high"

    def test_skips_short_clauses(self, mock_db_session):
        """Should skip clauses shorter than min_length."""
        with patch(
            "services.contract_service.check_clause_against_patterns",
            return_value=[{"why_invalid": "test", "risk_level": "high"}],
        ):
            issues = asyncio.run(detect_legal_issues(mock_db_session, ["Short."], min_length=20))
            assert issues == []

    def test_deduplicates_identical_issues(self, mock_db_session):
        """Should not include duplicate issues."""
        mock_match = {
            "why_invalid": "Invalid clause",
            "risk_level": "high",
            "legal_basis": "BGB § 551",
        }

        with patch(
            "services.contract_service.check_clause_against_patterns",
            return_value=[mock_match],
        ):
            issues = asyncio.run(detect_legal_issues(
                mock_db_session,
                ["Erste Klausel mit Problem.", "Zweite Klausel mit Problem."],
                min_length=5,
            ))
            # Both clauses produce identical descriptions, so only 1 issue
            assert len(issues) == 1

    def test_respects_max_issues_limit(self, mock_db_session):
        """Should limit the number of returned issues to max_issues."""
        mock_match = {
            "why_invalid": "Issue",
            "risk_level": "low",
        }

        with patch(
            "services.contract_service.check_clause_against_patterns",
            return_value=[mock_match],
        ):
            # Create 20 unique clauses that each produce a unique description
            clauses = [f"Einzigartige Klausel Nummer {i}" for i in range(20)]
            issues = asyncio.run(detect_legal_issues(
                mock_db_session, clauses, min_length=5, max_issues=5
            ))
            assert len(issues) == 5


# ============================================================
# Tests for save_upload_file
# ============================================================


class TestSaveUploadFile:
    def test_saves_file(self, tmp_path, monkeypatch):
        """Should save file to disk and return path and size."""
        # Override upload dir to temp path
        import services.contract_service as svc

        monkeypatch.setattr(svc.settings, "UPLOAD_DIR", str(tmp_path))

        file_obj = BytesIO(b"mock pdf content")
        file_path, file_size = save_upload_file(file_obj, "test.pdf")

        assert file_path.endswith("test.pdf")
        assert file_size == len(b"mock pdf content")
        # File should exist on disk
        import os

        assert os.path.exists(file_path)

    def test_creates_upload_directory(self, tmp_path, monkeypatch):
        """Should create upload directory if it doesn't exist."""
        import services.contract_service as svc

        nested_dir = tmp_path / "uploads" / "contracts"
        monkeypatch.setattr(svc.settings, "UPLOAD_DIR", str(nested_dir))

        assert not nested_dir.exists()
        save_upload_file(BytesIO(b"data"), "test.pdf")
        assert nested_dir.exists()
