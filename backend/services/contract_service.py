"""
Contract analysis service.
Handles PDF processing, text extraction, NLP analysis, and legal issue detection.
This service contains the core business logic extracted from the routers.

Pipeline:
  PDF → Better OCR → Text Cleaning → Section Splitting (§1, §2...)
    ↓
  Rule-based checks (Kaution, Kündigungsfrist, 3-Monatsregel etc.) → fast flags
    ↓
  Cleaned sections → Vector search (top-3 patterns + BGB text) → LLM judge
    ↓
  Output with confidence score + exact quote + legal citation
"""

import os
import re
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
from ocr_postprocess import extract_sections
from legal_kb.retrieval import (
    retrieve_top_invalid_patterns,
    retrieve_bgb_excerpts_for_patterns,
)
from legal_kb.embeddings import embedding_service
from services.llm_judge import judge_section
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

# ====================
# Minimal Rule-Based Checks (fast flags)
# ====================

# Patterns for rule-based fast checks (only the most reliable)
RULE_BASED_CHECKS = [
    {
        "topic": "Kaution",
        "pattern": r"Kaution.*(?:4|vier|5|fünf|6|sechs)\s*(?:Monatsmieten|Monatsmiete|Monaten)",
        "description": "Kaution übersteigt das gesetzliche Maximum von 3 Monatsmieten",
        "legal_basis": "BGB § 551 Abs. 1",
        "risk_level": "high",
    },
    {
        "topic": "Kaution",
        "pattern": r"Kaution.*(?:sofort|einmalig|in voller Höhe|auf einmal)\s*(?:fällig|zahlbar)",
        "description": "Kaution ist nicht in drei Raten zahlbar (gesetzlich vorgeschrieben)",
        "legal_basis": "BGB § 551 Abs. 2",
        "risk_level": "high",
    },
    {
        "topic": "Kündigung",
        "pattern": r"(?:Kündigungsfrist|kündigen).*(?:1\s*Monat|2\s*Monate)\s*(?:zum|vor)",
        "description": "Verkürzte Kündigungsfrist (< 3 Monate) – gesetzliche Mindestfrist beträgt 3 Monate",
        "legal_basis": "BGB § 573c",
        "risk_level": "high",
    },
    {
        "topic": "Mietminderung",
        "pattern": r"(?:Verzicht|Ausschluss)\s*(?:auf|der)\s*(?:Mietminderung|Mängelrechte)",
        "description": "Verzicht auf Mietminderung ist unwirksam",
        "legal_basis": "BGB § 536",
        "risk_level": "high",
    },
    {
        "topic": "Schönheitsreparaturen",
        "pattern": r"(?:Endrenovierung|Schlussrenovierung|vollständig\s*renoviert)",
        "description": "Endrenovierungsklausel unabhängig vom Zustand ist unwirksam",
        "legal_basis": "BGH VIII ZR 316/09",
        "risk_level": "high",
    },
    {
        "topic": "Kaution",
        "pattern": r"Kaution.*(?:unverzinslich|ohne.*Verzinsung|nicht.*verzinst)",
        "description": "Kaution muss verzinslich und getrennt angelegt werden",
        "legal_basis": "BGB § 551 Abs. 3",
        "risk_level": "medium",
    },
]


def _run_rule_based_checks(section_text: str) -> List[ContractIssue]:
    """
    Run minimal, highly reliable rule-based checks on a section.
    These are fast regex-based flags for the most common illegal patterns.

    Args:
        section_text: The contract section text to check.

    Returns:
        List of ContractIssue objects for matched rules.
    """
    issues = []
    for check in RULE_BASED_CHECKS:
        if re.search(check["pattern"], section_text, re.IGNORECASE):
            issues.append(
                ContractIssue(
                    description=check["description"],
                    risk_level=check["risk_level"],
                    legal_basis=check["legal_basis"],
                    clause_snippet=section_text[:200],
                    confidence=0.95,  # Rule-based checks are high confidence
                    exact_quote=section_text[:200],
                    legal_citation=check["legal_basis"],
                    detection_method="rule_based",
                )
            )
    return issues


# ====================
# Core Service Functions
# ====================


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

    Three strategies, tried in order:
      1. Regex-based section extraction (§ 1, 1., etc.) — best for German legal docs
      2. Double newline (paragraph) splitting
      3. spaCy sentence splitting (fallback)

    Args:
        text: The full extracted text
        doc: A spaCy Doc object (for sentence fallback)

    Returns:
        List of clause text strings
    """
    # Strategy 1: Regex section extraction for German legal documents
    sections = extract_sections(text)
    if len(sections) > 1:
        return sections

    # Strategy 2: Try splitting by double newlines first (paragraphs)
    clauses = [clause.strip() for clause in text.split("\n\n") if clause.strip()]

    # Strategy 3: Fall back to sentences if no paragraph splits found
    if not clauses:
        clauses = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    return clauses


def detect_legal_issues(
    db: Session,
    clauses: List[str],
    min_length: int = 20,
    max_issues: int = 10,
) -> List[ContractIssue]:
    """
    Enhanced legal issue detection with new pipeline:
    1. Rule-based fast checks → fast flags
    2. Vector search (top-3 patterns + BGB text) → LLM judge

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

        # --- Step 1: Minimal Rule-Based Checks (fast flags) ---
        rule_issues = _run_rule_based_checks(clause)
        for issue in rule_issues:
            desc_sig = issue.description[:80]
            if desc_sig not in seen_descriptions:
                seen_descriptions.add(desc_sig)
                issues.append(issue)

        # --- Step 2: Vector search → LLM judge ---
        # Generate embedding for this section
        section_embedding = embedding_service.encode_single(clause)

        # Retrieve top-3 most relevant invalid patterns
        top_patterns = retrieve_top_invalid_patterns(
            db,
            section_embedding,
            limit=settings.LLM_SEARCH_LIMIT,
            similarity_threshold=0.6,
        )

        if not top_patterns:
            # No relevant patterns found for this section, skip LLM
            continue

        # Retrieve exact BGB text excerpts for the matched patterns
        bgb_excerpts = retrieve_bgb_excerpts_for_patterns(db, top_patterns, limit=3)

        # --- Step 3: Call LLM judge ---
        llm_result = judge_section(
            section_text=clause,
            top_patterns=top_patterns,
            bgb_excerpts=bgb_excerpts,
        )

        if llm_result.get("ocr_error"):
            # OCR quality issue flagged
            desc = "OCR error – manual review needed"
            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                issues.append(
                    ContractIssue(
                        description=desc,
                        risk_level="medium",
                        legal_basis=None,
                        clause_snippet=clause[:200],
                        confidence=0.0,
                        exact_quote=clause[:200],
                        legal_citation=None,
                        detection_method="ocr_error",
                    )
                )
            continue

        if (
            llm_result.get("flag")
            and llm_result.get("confidence", 0) >= settings.LLM_CONFIDENCE_THRESHOLD
        ):
            # Flagged by LLM with sufficient confidence
            # Use the matched pattern info for legal basis / topic
            matched_topic = llm_result.get("matched_pattern")
            matched_pattern_info = None
            for p in top_patterns:
                if (
                    p.get("topic") == matched_topic
                    or p.get("clause_pattern") == matched_topic
                ):
                    matched_pattern_info = p
                    break
            if not matched_pattern_info:
                matched_pattern_info = top_patterns[0] if top_patterns else None

            desc = (
                f"LLM-flagged: {llm_result.get('reason', 'Potential invalid clause')[:150]}. "
                f"Pattern: {matched_pattern_info.get('topic', 'unknown') if matched_pattern_info else 'unknown'}"
            )

            if desc not in seen_descriptions:
                seen_descriptions.add(desc)
                issues.append(
                    ContractIssue(
                        description=desc,
                        risk_level=(
                            matched_pattern_info.get("risk_level", "medium")
                            if matched_pattern_info
                            else "medium"
                        ),
                        legal_basis=(
                            matched_pattern_info.get("legal_basis", None)
                            if matched_pattern_info
                            else None
                        ),
                        clause_snippet=clause[:200],
                        similarity=(
                            matched_pattern_info.get("similarity", None)
                            if matched_pattern_info
                            else None
                        ),
                        confidence=llm_result.get("confidence", 0.0),
                        exact_quote=llm_result.get("exact_quote"),
                        legal_citation=(
                            llm_result.get("legal_citation")
                            or (
                                matched_pattern_info.get("bgb_citation")
                                if matched_pattern_info
                                else None
                            )
                        ),
                        detection_method="llm",
                    )
                )

    # Limit to max_issues, prioritizing high-risk ones
    issues.sort(
        key=lambda x: (
            0 if x.risk_level == "high" else 1 if x.risk_level == "medium" else 2,
            -(x.confidence or 0),
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

    Pipeline:
      PDF → OCR → Section Splitting → Rule-based checks → Vector search → LLM judge

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
