"""
Contract analysis service.
Handles PDF processing, text extraction, NLP analysis, and legal issue detection.
This service contains the core business logic extracted from the routers.
"""

import os
import shutil
import time
import uuid
from typing import List, Tuple

import spacy
from sqlalchemy.orm import Session

from core.config import settings
from core.exceptions import BadRequestException, FileProcessingException
from core.logging import get_logger
from models.contract import Contract, ContractAnalysis
from ocr_utils import process_pdf_file
from legal_kb.retrieval import check_clause_against_patterns
from schemas.contract import (
    ContractAnalysisResponse,
    ContractAnalysisResult,
    ContractIssue,
    NamedEntity,
)

logger = get_logger(__name__)

# German rental contract key terms for matching
KEY_TERMS = [
    "Miete",
    "Kaution",
    "Kündigungsfrist",
    "Nebenkosten",
    "Schadensersatz",
    "Vertragsdauer",
    "Kündigung",
    "Mieterhöhung",
    "Provision",
    "Renovierung",
    "Mietvertrag",
    "Wohnung",
    "Vermieter",
    "Mieter",
    "Mietobjekt",
]

# Map processing method to frontend expected ocr_used value
OCR_USED_MAP = {
    "text_extraction": "none",
    "ocr": "primary",
    "ocr_fallback": "fallback",
}


def save_upload_file(file_obj, filename: str) -> Tuple[str, int]:
    """
    Save an uploaded file to disk with a unique name.

    Args:
        file_obj: The uploaded file object (must have .file attribute)
        filename: Original filename

    Returns:
        Tuple of (file_path, file_size_in_bytes)
    """
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file_obj, buffer)

    file_size = os.path.getsize(file_path)
    logger.info("Saved uploaded file: %s (%d bytes)", unique_filename, file_size)
    return file_path, file_size


def validate_pdf(filename: str) -> None:
    """Validate that the uploaded file is a PDF."""
    if not filename or not filename.lower().endswith(".pdf"):
        raise BadRequestException("Only PDF files are supported")


def extract_text_from_pdf(file_path: str) -> Tuple[str, str]:
    """
    Extract text from a PDF file, using OCR if needed.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (extracted_text, processing_method)
    """
    start_time = time.time()
    extracted_text, processing_method = process_pdf_file(file_path)
    processing_time = time.time() - start_time

    logger.info(
        "Text extraction completed: method=%s, time=%.2fs, length=%d chars",
        processing_method,
        processing_time,
        len(extracted_text) if extracted_text else 0,
    )

    if not extracted_text or not extracted_text.strip():
        raise FileProcessingException("Could not extract text from PDF")

    return extracted_text, processing_method


def analyze_text_with_spacy(
    doc: spacy.tokens.Doc,
) -> Tuple[int, int, List[str], List[dict]]:
    """
    Perform basic NLP analysis on the extracted text using spaCy.

    Args:
        doc: A spaCy Doc object

    Returns:
        Tuple of (word_count, sentence_count, found_key_terms, named_entities)
    """
    # Word count (excluding punctuation and spaces)
    word_count = len(
        [token for token in doc if not token.is_punct and not token.is_space]
    )

    # Sentence count
    sentence_count = len(list(doc.sents))

    # Named entities (filtered for contract-relevant labels)
    relevant_labels = {"PERSON", "ORG", "GPE", "MONEY", "DATE"}
    entities = [
        {"text": ent.text, "label": ent.label_}
        for ent in doc.ents
        if ent.label_ in relevant_labels
    ]

    # Key term matching
    extracted_text_lower = doc.text.lower()
    found_key_terms = [
        term for term in KEY_TERMS if term.lower() in extracted_text_lower
    ]

    return word_count, sentence_count, found_key_terms, entities


def split_into_clauses(text: str, doc: spacy.tokens.Doc) -> List[str]:
    """
    Split contract text into individual clauses for analysis.

    Args:
        text: The full extracted text
        doc: A spaCy Doc object (for sentence fallback)

    Returns:
        List of clause text strings
    """
    # Try splitting by double newlines first (paragraphs)
    clauses = [clause.strip() for clause in text.split("\n\n") if clause.strip()]

    # Fall back to sentences if no paragraph splits found
    if not clauses:
        clauses = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return clauses


def detect_legal_issues(
    db: Session, clauses: List[str], min_length: int = 20, max_issues: int = 10
) -> List[ContractIssue]:
    """
    Check each clause against known invalid clause patterns.

    Args:
        db: Database session
        clauses: List of clause texts
        min_length: Skip clauses shorter than this
        max_issues: Maximum number of issues to return

    Returns:
        List of ContractIssue objects
    """
    issues = []
    seen_descriptions = set()

    for clause in clauses:
        if len(clause) < min_length:
            continue

        matches = check_clause_against_patterns(db, clause)
        for match in matches:
            description = (
                f"Potential invalid clause: '{clause[:100]}...' "
                f"- {match['why_invalid']} "
                f"(Risk: {match['risk_level']})"
            )
            if match.get("legal_basis"):
                description += f" - Legal basis: {match['legal_basis']}"

            # Deduplicate
            if description not in seen_descriptions:
                seen_descriptions.add(description)
                issues.append(
                    ContractIssue(
                        description=description,
                        risk_level=match.get("risk_level"),
                        legal_basis=match.get("legal_basis"),
                        clause_snippet=clause[:200],
                        similarity=match.get("similarity"),
                    )
                )

    return issues[:max_issues]


def create_contract_record(
    db: Session,
    filename: str,
    file_path: str,
    file_size: int,
    processing_method: str,
) -> Contract:
    """Create a Contract database record."""
    contract = Contract(
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type="application/pdf",
        processing_method=processing_method,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    logger.info("Created contract record: id=%d, filename=%s", contract.id, filename)
    return contract


def create_analysis_record(
    db: Session,
    contract_id: int,
    extracted_text: str,
    word_count: int,
    sentence_count: int,
    key_terms: List[str],
    entities: List[dict],
    issues: List[str],
    processing_time: int,
    ocr_used: str,
) -> ContractAnalysis:
    """Create a ContractAnalysis database record."""
    analysis = ContractAnalysis(
        contract_id=contract_id,
        extracted_text=extracted_text,
        word_count=word_count,
        sentence_count=sentence_count,
        key_terms=key_terms,
        named_entities=entities,
        potential_issues=issues,
        processing_time_seconds=processing_time,
        ocr_used=ocr_used,
    )
    db.add(analysis)
    db.commit()
    return analysis


def analyze_contract(
    db: Session,
    file_obj,
    filename: str,
    nlp: spacy.Language,
) -> Tuple[ContractAnalysisResponse, float]:
    """
    Full contract analysis pipeline: validate, extract, analyze, detect issues.

    Args:
        db: Database session
        file_obj: Uploaded file object
        filename: Original filename
        nlp: Loaded spaCy model

    Returns:
        Tuple of (ContractAnalysisResponse, processing_time_seconds)
    """
    # 1. Validate file
    validate_pdf(filename)

    # 2. Save file
    file_path, file_size = save_upload_file(file_obj, filename)

    # 3. Extract text + NLP analysis + issue detection (timed)
    start_time = time.time()
    extracted_text, processing_method = extract_text_from_pdf(file_path)
    doc = nlp(extracted_text)
    word_count, sentence_count, found_key_terms, entities = analyze_text_with_spacy(doc)
    clauses = split_into_clauses(extracted_text, doc)
    issue_objects = detect_legal_issues(db, clauses)
    processing_time = time.time() - start_time

    # 4. Map OCR used
    ocr_used = OCR_USED_MAP.get(processing_method, "none")

    # 5. Save to database
    contract = create_contract_record(
        db, filename, file_path, file_size, processing_method
    )

    # Serialize issues to strings for DB storage (legacy field)
    issue_strings = [
        (
            f"{issue.description} (Risk: {issue.risk_level})"
            if issue.legal_basis
            else issue.description
        )
        for issue in issue_objects
    ]

    create_analysis_record(
        db,
        contract.id,
        extracted_text,
        word_count,
        sentence_count,
        found_key_terms,
        entities,
        issue_strings,
        int(processing_time),
        ocr_used,
    )

    # 6. Build and return response
    response = ContractAnalysisResponse(
        filename=filename,
        contract_id=contract.id,
        processing_method=processing_method,
        ocr_used=ocr_used,
        processing_time_seconds=int(processing_time),
        analysis=ContractAnalysisResult(
            word_count=word_count,
            sentences=sentence_count,
            key_terms=found_key_terms,
            entities=[NamedEntity(text=e["text"], label=e["label"]) for e in entities],
            issues=issue_objects,
        ),
    )
    return response, processing_time
