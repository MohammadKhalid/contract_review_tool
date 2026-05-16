"""
Shared test fixtures and configuration for backend tests.
"""

from unittest.mock import MagicMock, Mock, patch
from typing import Any, Dict, Generator, List, Tuple
from io import BytesIO

import pytest
from sqlalchemy.orm import Session

# ============================================================
# Mock helpers
# ============================================================


class MockToken:
    """Mock for spaCy Token objects."""

    def __init__(self, text: str, is_punct: bool = False, is_space: bool = False):
        self.text = text
        self.is_punct = is_punct
        self.is_space = is_space


class MockSpan:
    """Mock for spaCy Span objects used in sentencizer."""

    def __init__(self, text: str):
        self.text = text


class MockEntity:
    """Mock for spaCy named entities."""

    def __init__(self, text: str, label_: str):
        self.text = text
        self.label_ = label_


class MockDoc:
    """
    Mock for spaCy Doc object.
    Provides sents, entities, text, and token iteration.
    """

    def __init__(self, text: str):
        self.text = text
        self.ents: List[MockEntity] = []
        self._sents: List[MockSpan] = [
            MockSpan(s.strip())
            for s in text.replace("\n\n", "\n").split(".")
            if s.strip()
        ]

    def __iter__(self):
        """Simulate token iteration (splits on whitespace and punctuation)."""
        for word in self.text.split():
            is_punct = word in {",", ".", "!", "?", ";", ":", "(", ")", "[", "]"}
            is_space = False
            yield MockToken(word, is_punct=is_punct, is_space=is_space)

    @property
    def sents(self):
        return self._sents

    def __len__(self):
        return len(self.text)


def make_mock_nlp():
    """Create a mock spaCy Language pipeline that returns MockDoc."""
    mock = MagicMock()
    mock.return_value = MockDoc
    return mock


# ============================================================
# Database fixtures
# ============================================================


@pytest.fixture
def mock_db_session():
    """Create a mock SQLAlchemy Session."""
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    session.query = MagicMock()
    return session


# ============================================================
# File upload fixture
# ============================================================


@pytest.fixture
def mock_upload_file():
    """Create a mock uploaded file object with .file attribute."""
    file_obj = MagicMock()
    file_obj.file = BytesIO(b"%PDF-1.4 mock pdf content")
    return file_obj


# ============================================================
# Sample contract text fixture
# ============================================================


@pytest.fixture
def sample_contract_text():
    """Sample German rental contract text for testing."""
    return """
MIETVERTRAG

Zwischen Vermieter Max Mustermann und Mieter John Doe wird folgender Mietvertrag geschlossen.

§ 1 Mietobjekt
Die Wohnung befindet sich in der Musterstraße 1, 10115 Berlin.

§ 2 Miete
Die monatliche Miete beträgt 800 Euro.

§ 3 Kaution
Der Mieter leistet eine Kaution in Höhe von vier Monatsmieten.

§ 4 Nebenkosten
Die Nebenkosten betragen pauschal 150€ pro Monat.

§ 5 Haustiere
Haustiere sind in der Wohnung nicht gestattet.

§ 6 Kündigung
Der Mieter kann mit einer Frist von 1 Monat kündigen.

Berlin, den 01.01.2024
"""


@pytest.fixture
def sample_mock_doc(sample_contract_text):
    """MockDoc instance for the sample contract text."""
    doc = MockDoc(sample_contract_text)
    # Add some mock entities
    doc.ents = [
        MockEntity("Max Mustermann", "PERSON"),
        MockEntity("John Doe", "PERSON"),
        MockEntity("Berlin", "GPE"),
        MockEntity("800 Euro", "MONEY"),
    ]
    return doc


@pytest.fixture
def mock_nlp_model():
    """Mock spaCy Language model that returns MockDoc."""

    def nlp_pipeline(text: str) -> MockDoc:
        doc = MockDoc(text)
        doc.ents = [
            MockEntity("Max Mustermann", "PERSON"),
            MockEntity("John Doe", "PERSON"),
            MockEntity("Berlin", "GPE"),
        ]
        return doc

    return nlp_pipeline


# ============================================================
# OCR / PDF fixtures
# ============================================================


@pytest.fixture
def mock_pdf_processing(monkeypatch):
    """Mock the process_pdf_file function in ocr_utils."""

    def mock_process(file_path: str) -> Tuple[str, str]:
        return "Mietvertrag text from mock PDF", "text_extraction"

    import ocr_utils

    monkeypatch.setattr(ocr_utils, "process_pdf_file", mock_process)
    return mock_process


# ============================================================
# Invalid clause pattern results fixture
# ============================================================


@pytest.fixture
def mock_clause_pattern_matches():
    """Sample invalid clause pattern matches."""
    return [
        {
            "id": 1,
            "topic": "Kaution",
            "clause_pattern": "Kaution übersteigt drei Monatsmieten",
            "why_invalid": "Gemäß BGB § 551 darf die Kaution das Dreifache der monatlichen Miete nicht übersteigen.",
            "legal_basis": "BGB § 551",
            "risk_level": "high",
            "similarity": 0.92,
        },
        {
            "id": 5,
            "topic": "Nebenkosten",
            "clause_pattern": "Pauschale Nebenkostenabrechnung ohne Nachweis",
            "why_invalid": "BetrKV verlangt eine detaillierte Abrechnung der tatsächlich entstandenen Kosten.",
            "legal_basis": "BetrKV § 2",
            "risk_level": "medium",
            "similarity": 0.85,
        },
    ]
