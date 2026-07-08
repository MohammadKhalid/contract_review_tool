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
from services.llm_judge import batch_judge_sections, judge_section_async
from schemas.contract import (
    ContractAnalysisResponse,
    ContractAnalysisResult,
    ContractIssue,
    NamedEntity,
)

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, Dict

logger = get_logger(__name__)


# ====================
# Timing utilities for performance observability (C + D)
# ====================
@contextmanager
def timed_phase(name: str, **extra: Any) -> Iterator[None]:
    """Context manager that logs elapsed time for a synchronous phase."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        extra_str = " ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
        logger.info("TIMING phase=%s duration=%.3fs %s", name, elapsed, extra_str)


@asynccontextmanager
async def async_timed_phase(name: str, **extra: Any) -> AsyncIterator[None]:
    """Async context manager that logs elapsed time for an async phase."""
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        extra_str = " ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
        logger.info("TIMING phase=%s duration=%.3fs %s", name, elapsed, extra_str)


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


def _get_rule_based_checks(lang: str = "de") -> list:
    """Return rule-based check definitions for the given language."""
    if lang == "en":
        return [
            {
                "topic": "Deposit",
                "pattern": r"Kaution.*(?:4|vier|5|fünf|6|sechs)\s*(?:Monatsmieten|Monatsmiete|Monaten)",
                "description": "Security deposit exceeds the legal maximum of 3 months' rent",
                "legal_basis": "BGB § 551 Abs. 1",
                "risk_level": "high",
            },
            {
                "topic": "Deposit",
                "pattern": r"Kaution.*(?:sofort|einmalig|in voller Höhe|auf einmal)\s*(?:fällig|zahlbar)",
                "description": "Security deposit is not payable in three installments (as legally required)",
                "legal_basis": "BGB § 551 Abs. 2",
                "risk_level": "high",
            },
            {
                "topic": "Termination",
                "pattern": r"(?:Kündigungsfrist|kündigen).*(?:1\s*Monat|2\s*Monate)\s*(?:zum|vor)",
                "description": "Shortened notice period (< 3 months) – statutory minimum is 3 months",
                "legal_basis": "BGB § 573c",
                "risk_level": "high",
            },
            {
                "topic": "Rent Reduction",
                "pattern": r"(?:Verzicht|Ausschluss)\s*(?:auf|der)\s*(?:Mietminderung|Mängelrechte)",
                "description": "Waiver of rent reduction rights is invalid",
                "legal_basis": "BGB § 536",
                "risk_level": "high",
            },
            {
                "topic": "Renovation",
                "pattern": r"(?:Endrenovierung|Schlussrenovierung|vollständig\s*renoviert)",
                "description": "End-renovation clause regardless of condition is invalid",
                "legal_basis": "BGH VIII ZR 316/09",
                "risk_level": "high",
            },
            {
                "topic": "Deposit",
                "pattern": r"Kaution.*(?:unverzinslich|ohne.*Verzinsung|nicht.*verzinst)",
                "description": "Security deposit must be interest-bearing and kept separately",
                "legal_basis": "BGB § 551 Abs. 3",
                "risk_level": "medium",
            },
        ]
    else:
        # German (default)
        return RULE_BASED_CHECKS


def _run_rule_based_checks(section_text: str, lang: str = "de") -> List[ContractIssue]:
    """
    Run minimal, highly reliable rule-based checks on a section.
    These are fast regex-based flags for the most common illegal patterns.

    Args:
        section_text: The contract section text to check.
        lang: Target language for descriptions ('en' or 'de').

    Returns:
        List of ContractIssue objects for matched rules.
    """
    checks = _get_rule_based_checks(lang)
    issues = []
    for check in checks:
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


async def detect_legal_issues(
    db: Session,
    clauses: List[str],
    min_length: int = 1,
    max_issues: int = 10,
    lang: str = "de",
) -> List[ContractIssue]:
    """
    Enhanced legal issue detection with batch embeddings + batched LLM judge.

    D step (after C async): groups clauses that need LLM judgment into
    batches of size LLM_BATCH_SIZE and sends them in far fewer calls via
    batch_judge_sections. Falls back to per-item if batch returns bad count.
    """
    lang = (lang or "de").lower()[:2]
    if lang not in ("en", "de"):
        lang = "de"

    all_issues: List[ContractIssue] = []
    seen_descriptions: set = set()

    long_clauses = [c for c in clauses if len(c) >= min_length]
    if not long_clauses:
        return []

    # Phase 1: Batch embeddings (fast win)
    with timed_phase("batch_embeddings", n_clauses=len(long_clauses)):
        embs = embedding_service.encode_batch(long_clauses)
    emb_map = dict(zip(long_clauses, embs))

    # Phase 2: Cheap pre-filter (rules + retrieval + threshold) — collect LLM candidates
    llm_candidates: List[dict] = (
        []
    )  # each carries everything needed for batch judge + issue building
    rule_issues_count = 0

    for clause in long_clauses:
        # Rule-based first (always)
        for iss in _run_rule_based_checks(clause, lang=lang):
            sig = iss.description[:80]
            if sig not in seen_descriptions:
                seen_descriptions.add(sig)
                all_issues.append(iss)
                rule_issues_count += 1

        emb = emb_map.get(clause)
        if emb is None:
            continue

        pats = retrieve_top_invalid_patterns(
            db, emb, limit=settings.LLM_SEARCH_LIMIT, similarity_threshold=0.6
        )
        if not pats:
            continue

        top_sim = pats[0].get("similarity", 0.0)
        if top_sim < settings.LLM_JUDGE_THRESHOLD:
            continue

        bgb = retrieve_bgb_excerpts_for_patterns(db, pats, limit=3)

        llm_candidates.append(
            {
                "clause": clause,
                "pats": pats,
                "bgb": bgb,
            }
        )

    # Phase 3: Batched LLM judge (the big win for D)
    llm_judgments: List[Dict[str, Any]] = []
    batch_size = max(1, getattr(settings, "LLM_BATCH_SIZE", 3))
    num_candidates = len(llm_candidates)

    if num_candidates > 0:
        # Group into batches
        groups = [
            llm_candidates[i : i + batch_size]
            for i in range(0, num_candidates, batch_size)
        ]
        num_batches = len(groups)

        async def _run_batch(group: List[dict]) -> List[Dict[str, Any]]:
            # Prepare input for batch_judge_sections
            sections = [
                {
                    "text": item["clause"],
                    "patterns": item["pats"],
                    "bgb": item["bgb"],
                }
                for item in group
            ]
            # One LLM call for the whole group (under semaphore to respect concurrency)
            sem = asyncio.Semaphore(max(1, settings.LLM_CONCURRENCY))
            async with sem:
                return await batch_judge_sections(sections, lang=lang)

        with timed_phase(
            "llm_batch_judge",
            candidates=num_candidates,
            batches=num_batches,
            batch_size=batch_size,
        ):
            batch_tasks = [_run_batch(g) for g in groups]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Flatten results in order
        for br in batch_results:
            if isinstance(br, Exception):
                logger.error("Batch LLM error: %s", br)
                # fallback: treat whole group as no flags
                continue
            llm_judgments.extend(br)

        # Safety: if count mismatch (rare), truncate or pad
        if len(llm_judgments) != num_candidates:
            logger.warning(
                "Batch judgment count mismatch: got %d expected %d — truncating/padding",
                len(llm_judgments),
                num_candidates,
            )
            while len(llm_judgments) < num_candidates:
                llm_judgments.append(
                    {"flag": False, "confidence": 0.0, "ocr_error": False}
                )
            llm_judgments = llm_judgments[:num_candidates]

        logger.info(
            "LLM batching summary: candidates=%d, batch_size=%d, batches=%d, actual_llm_calls=%d",
            num_candidates,
            batch_size,
            num_batches,
            num_batches,
        )

        # Now turn judgments into issues (same logic as before, using original candidate metadata)
        for cand, llm in zip(llm_candidates, llm_judgments):
            clause = cand["clause"]
            pats = cand["pats"]

            if llm.get("ocr_error"):
                # Language-aware description (so it translates when UI lang changes).
                # We include a short preview of the actual garbled text so each OCR
                # error is unique and the main card title already shows context.
                preview = (clause or "").strip()[:80]
                if lang == "en":
                    d = f'OCR quality issue: “{preview}...” – manual review needed'
                else:
                    d = f'OCR-Qualitätsproblem: „{preview}...“ – manuelle Prüfung empfohlen'

                # Do NOT deduplicate OCR errors. Each one refers to a different
                # unreadable section. We also attach the full text via exact_quote.
                all_issues.append(
                    ContractIssue(
                        description=d,
                        risk_level="medium",
                        detection_method="ocr_error",
                        clause_snippet=clause[:250],
                        exact_quote=clause[:250],
                    )
                )
                continue

            if (
                llm.get("flag")
                and llm.get("confidence", 0) >= settings.LLM_CONFIDENCE_THRESHOLD
            ):
                mp = next(
                    (p for p in pats if p.get("topic") == llm.get("matched_pattern")),
                    pats[0] if pats else None,
                )
                prefix, plabel = (
                    ("LLM-flagged", "Pattern")
                    if lang == "en"
                    else ("LLM-erfasst", "Muster")
                )
                d = f"{prefix}: {llm.get('reason', 'Potential invalid clause')} {plabel}: {mp.get('topic','unknown') if mp else 'unknown'}"

                if d not in seen_descriptions:
                    seen_descriptions.add(d)
                    all_issues.append(
                        ContractIssue(
                            description=d,
                            risk_level=(
                                mp.get("risk_level", "medium") if mp else "medium"
                            ),
                            legal_basis=mp.get("legal_basis") if mp else None,
                            clause_snippet=clause[:200],
                            confidence=llm.get("confidence"),
                            exact_quote=llm.get("exact_quote"),
                            legal_citation=llm.get("legal_citation")
                            or (mp.get("bgb_citation") if mp else None),
                            detection_method="llm",
                        )
                    )

    # Final sort + limit (rules + llm mixed)
    all_issues.sort(
        key=lambda x: (
            0 if x.risk_level == "high" else 1 if x.risk_level == "medium" else 2,
            -(x.confidence or 0),
        )
    )
    return all_issues[:max_issues]


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


async def analyze_contract(
    db: Session,
    file_obj,
    filename: str,
    nlp: spacy.Language,
    lang: str = "de",
) -> Tuple[ContractAnalysisResponse, float]:
    """
    Full contract analysis pipeline: validate, extract, analyze, detect issues.

    Pipeline:
      PDF → OCR → Section Splitting → Rule-based checks → Vector search → LLM judge

    Async to support non-blocking LLM I/O (C + D).

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

    # 3. Extract text + NLP analysis + issue detection (timed phases)
    # Offload all the blocking work (PDF rasterization via poppler, Tesseract OCR
    # subprocesses, spaCy CPU work) to a thread so the uvicorn event loop is not
    # blocked. This prevents the whole app from appearing stuck during long OCR
    # jobs (common for scanned contracts) and allows other requests to make progress.
    overall_start = time.time()

    with timed_phase("extract_text"):
        extracted_text, processing_method = await asyncio.to_thread(
            extract_text_from_pdf, file_path
        )

    with timed_phase("nlp_analysis"):
        def _run_nlp_and_stats(text: str):
            d = nlp(text)
            wc, sc, terms, ents = analyze_text_with_spacy(d)
            return wc, sc, terms, ents, d

        word_count, sentence_count, found_key_terms, entities, doc = await asyncio.to_thread(
            _run_nlp_and_stats, extracted_text
        )

    # Normalize language
    lang = (lang or "de").lower()[:2]
    if lang not in ("en", "de"):
        lang = "de"

    clauses = split_into_clauses(extracted_text, doc)

    with timed_phase("detect_legal_issues", clauses=len(clauses)):
        issue_objects = await detect_legal_issues(db, clauses, lang=lang)

    processing_time = time.time() - overall_start

    logger.info(
        "Analysis timing | total=%.2fs | clauses=%d | issues_found=%d",
        processing_time,
        len(clauses),
        len(issue_objects),
    )

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
