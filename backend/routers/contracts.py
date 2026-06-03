"""
Contract upload and analysis API endpoints.
Thin router that delegates business logic to the contract service.
"""

import asyncio
import logging

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import spacy

from core.auth import get_current_principal, Principal
from core.dependencies import get_db, get_nlp_model
from core.exceptions import AppException, BadRequestException, FileProcessingException
from core.logging import get_logger
from schemas.contract import ContractAnalysisResponse
from services.contract_service import analyze_contract

logger = get_logger(__name__)

router = APIRouter(prefix="/contracts")


@router.post(
    "/analyze",
    response_model=ContractAnalysisResponse,
    summary="Upload and analyze a contract PDF",
    description="Uploads a PDF contract, extracts text (with OCR fallback), "
    "performs NLP analysis, and detects potential legal issues "
    "using the legal knowledge base.",
)
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    lang: str = Query("de", description="Language for issue descriptions ('en' or 'de')"),
    db: Session = Depends(get_db),
    nlp: spacy.Language = Depends(get_nlp_model),
    principal: Principal = Depends(lambda: get_current_principal(increment_usage=1)),
):
    """
    Upload and analyze a contract PDF.
    Requires a valid access token (admin key or Polar license key after payment).
    Extracts text, performs legal analysis using knowledge base, and returns results.
    """
    try:
        # Normalize language early
        lang = (lang or "de").lower()[:2]
        if lang not in ("en", "de"):
            lang = "de"

        # Call the async analysis pipeline directly
        response, _ = await analyze_contract(
            db=db,
            file_obj=file.file,
            filename=file.filename or "unknown.pdf",
            nlp=nlp,
            lang=lang,
        )
        return response

    except BadRequestException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except FileProcessingException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("Error analyzing contract: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze contract: {str(e)}"
        )
