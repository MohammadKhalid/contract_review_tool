from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import PyPDF2
import spacy
import os
import shutil
import time
from datetime import datetime

# Import our modules
from ocr_utils import process_pdf_file
from database.connection import get_db, create_tables
from models.contract import Contract, ContractAnalysis

app = FastAPI(title="German Rental Contract Review API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load German spaCy model
try:
    nlp = spacy.load("de_core_news_sm")
except OSError:
    print("Downloading German spaCy model...")
    os.system("python -m spacy download de_core_news_sm")
    nlp = spacy.load("de_core_news_sm")


def analyze_contract(text):
    """Basic contract analysis using spaCy"""
    doc = nlp(text)

    analysis = {
        "word_count": len(doc),
        "sentences": len(list(doc.sents)),
        "entities": [{"text": ent.text, "label": ent.label_} for ent in doc.ents],
        "key_terms": [],
        "issues": [],
    }

    # Basic keyword detection for rental contracts
    key_terms = [
        "Miete",
        "Kaution",
        "Kündigung",
        "Vertrag",
        "Wohnung",
        "Mieter",
        "Vermieter",
    ]
    for term in key_terms:
        if term.lower() in text.lower():
            analysis["key_terms"].append(term)

    # Basic issue detection (simplified)
    if "kaution" in text.lower() and "3 monatsmieten" not in text.lower():
        analysis["issues"].append("Kaution might exceed 3 months rent")

    return analysis


def save_contract_to_db(
    db: Session,
    filename: str,
    file_path: str,
    file_size: int,
    mime_type: str,
    processing_method: str,
    extracted_text: str,
    analysis_result: dict,
    processing_time: int,
    ocr_used: str,
):
    """Save contract and analysis results to database"""

    # Create contract record
    contract = Contract(
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        processing_method=processing_method,
    )
    db.add(contract)
    db.flush()  # Get the contract ID

    # Create analysis record
    analysis = ContractAnalysis(
        contract_id=contract.id,
        extracted_text=extracted_text,
        word_count=analysis_result.get("word_count"),
        sentence_count=analysis_result.get("sentences"),
        key_terms=analysis_result.get("key_terms", []),
        named_entities=analysis_result.get("entities", []),
        potential_issues=analysis_result.get("issues", []),
        processing_time_seconds=processing_time,
        ocr_used=ocr_used,
    )
    db.add(analysis)
    db.commit()

    return contract.id


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/contracts")
async def get_contracts(db: Session = Depends(get_db), skip: int = 0, limit: int = 10):
    """Get list of analyzed contracts"""
    contracts = (
        db.query(Contract)
        .order_by(Contract.upload_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for contract in contracts:
        # Get the latest analysis for each contract
        latest_analysis = (
            db.query(ContractAnalysis)
            .filter(ContractAnalysis.contract_id == contract.id)
            .order_by(ContractAnalysis.analysis_date.desc())
            .first()
        )

        contract_data = {
            "id": contract.id,
            "filename": contract.filename,
            "upload_date": contract.upload_date.isoformat(),
            "file_size": contract.file_size,
            "processing_method": contract.processing_method,
            "analysis": None,
        }

        if latest_analysis:
            contract_data["analysis"] = {
                "word_count": latest_analysis.word_count,
                "sentence_count": latest_analysis.sentence_count,
                "key_terms": latest_analysis.key_terms,
                "named_entities": latest_analysis.named_entities,
                "potential_issues": latest_analysis.potential_issues,
                "processing_time_seconds": latest_analysis.processing_time_seconds,
                "ocr_used": latest_analysis.ocr_used,
                "analysis_date": latest_analysis.analysis_date.isoformat(),
            }

        result.append(contract_data)

    return {"contracts": result, "total": len(result)}


@app.get("/contracts/{contract_id}")
async def get_contract_detail(contract_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific contract"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    # Get all analyses for this contract
    analyses = (
        db.query(ContractAnalysis)
        .filter(ContractAnalysis.contract_id == contract_id)
        .order_by(ContractAnalysis.analysis_date.desc())
        .all()
    )

    contract_data = {
        "id": contract.id,
        "filename": contract.filename,
        "upload_date": contract.upload_date.isoformat(),
        "file_size": contract.file_size,
        "mime_type": contract.mime_type,
        "processing_method": contract.processing_method,
        "analyses": [],
    }

    for analysis in analyses:
        analysis_data = {
            "id": analysis.id,
            "analysis_date": analysis.analysis_date.isoformat(),
            "word_count": analysis.word_count,
            "sentence_count": analysis.sentence_count,
            "key_terms": analysis.key_terms,
            "named_entities": analysis.named_entities,
            "potential_issues": analysis.potential_issues,
            "processing_time_seconds": analysis.processing_time_seconds,
            "ocr_used": analysis.ocr_used,
            "extracted_text_preview": (
                analysis.extracted_text[:500] + "..."
                if analysis.extracted_text and len(analysis.extracted_text) > 500
                else analysis.extracted_text
            ),
        }
        contract_data["analyses"].append(analysis_data)

    return contract_data


@app.post("/analyze")
async def analyze_contract_endpoint(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    # Validate file extension
    allowed_extensions = {".pdf", ".txt"}
    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and TXT files are allowed.",
        )

    # Save uploaded file temporarily
    temp_path = f"/tmp/{file.filename}"
    start_time = time.time()

    try:
        # Read file content and get file size
        file_content = await file.read()
        file_size = len(file_content)

        with open(temp_path, "wb") as buffer:
            buffer.write(file_content)

        # Extract text based on file type
        if file_extension == ".pdf":
            extracted_text, processing_method = process_pdf_file(temp_path)
            ocr_used = (
                "primary"
                if processing_method == "ocr"
                else ("fallback" if processing_method == "ocr_fallback" else "none")
            )
        else:
            # For text files, just read the content
            with open(temp_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
            processing_method = "text_file"
            ocr_used = "none"

        # Analyze the extracted text
        analysis_result = analyze_contract(extracted_text)

        # Calculate processing time
        processing_time = int(time.time() - start_time)

        # Save to database
        contract_id = save_contract_to_db(
            db=db,
            filename=file.filename,
            file_path=temp_path,  # In production, you'd save to persistent storage
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            processing_method=processing_method,
            extracted_text=extracted_text,
            analysis_result=analysis_result,
            processing_time=processing_time,
            ocr_used=ocr_used,
        )

        return {
            "filename": file.filename,
            "contract_id": contract_id,
            "processing_method": processing_method,
            "ocr_used": ocr_used,
            "processing_time_seconds": processing_time,
            "analysis": analysis_result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    try:
        print("Initializing database connection...")
        create_tables()
        print("✅ Database tables created/verified successfully")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print("The application may not work correctly without database access")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
