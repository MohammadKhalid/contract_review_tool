"""
Contract upload and analysis API endpoints.
Handles PDF contract uploads, text extraction, and legal analysis using knowledge base.
"""

import logging
import os
import shutil
import time
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import spacy

from database.connection import get_db
from models.contract import Contract, ContractAnalysis
from ocr_utils import process_pdf_file
from legal_kb.retrieval import check_clause_against_patterns

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts")

# Load German spaCy model
nlp = spacy.load("de_core_news_sm")

# German rental contract key terms
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


@router.post("/analyze")
async def analyze_contract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and analyze a contract PDF.
    Extracts text, performs legal analysis using knowledge base, and returns results.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads/contracts"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, unique_filename)

        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Process PDF and extract text
        start_time = time.time()
        extracted_text, processing_method = process_pdf_file(file_path)
        processing_time = time.time() - start_time

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400, detail="Could not extract text from PDF"
            )

        # Map processing method to frontend expected ocr_used
        ocr_used_map = {
            "text_extraction": "none",
            "ocr": "primary",
            "ocr_fallback": "fallback",
        }
        ocr_used = ocr_used_map.get(processing_method, "none")

        # Create Contract record
        contract = Contract(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            processing_method=processing_method,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        # Perform analysis using spaCy
        doc = nlp(extracted_text)

        # Basic statistics
        word_count = len(
            [token for token in doc if not token.is_punct and not token.is_space]
        )
        sentence_count = len(list(doc.sents))

        # Named entities
        entities = [
            {"text": ent.text, "label": ent.label_}
            for ent in doc.ents
            if ent.label_
            in ["PERSON", "ORG", "GPE", "MONEY", "DATE"]  # Relevant for contracts
        ]

        # Key terms (simple matching)
        found_key_terms = [
            term for term in KEY_TERMS if term.lower() in extracted_text.lower()
        ]

        # Legal analysis using knowledge base
        potential_issues = []

        # Split text into clauses (by double newlines or sentences)
        clauses = [
            clause.strip() for clause in extracted_text.split("\n\n") if clause.strip()
        ]
        if not clauses:
            clauses = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        # Check each clause against invalid patterns
        for clause in clauses:
            if len(clause) < 20:  # Skip very short clauses
                continue

            matches = check_clause_against_patterns(db, clause)
            for match in matches:
                issue_text = f"Potential invalid clause: '{clause[:100]}...' - {match['why_invalid']} (Risk: {match['risk_level']}) - Legal basis: {match['legal_basis']}"
                potential_issues.append(issue_text)

        # Remove duplicates and limit to top 10
        potential_issues = list(set(potential_issues))[:10]

        # Create ContractAnalysis record
        analysis = ContractAnalysis(
            contract_id=contract.id,
            extracted_text=extracted_text,
            word_count=word_count,
            sentence_count=sentence_count,
            key_terms=found_key_terms,
            named_entities=entities,
            potential_issues=potential_issues,
            processing_time_seconds=int(processing_time),
            ocr_used=ocr_used,
        )
        db.add(analysis)
        db.commit()

        # Return response matching frontend expectations
        return {
            "filename": file.filename,
            "contract_id": contract.id,
            "processing_method": processing_method,
            "ocr_used": ocr_used,
            "processing_time_seconds": int(processing_time),
            "analysis": {
                "word_count": word_count,
                "sentences": sentence_count,  # Frontend uses 'sentences'
                "key_terms": found_key_terms,
                "entities": entities,
                "issues": potential_issues,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing contract: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze contract: {str(e)}"
        )
