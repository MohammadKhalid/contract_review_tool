from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import PyPDF2
import spacy
import os
import shutil

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


def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    with open(file_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


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


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze_contract_endpoint(file: UploadFile = File(...)):
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
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract text and analyze
        if file_extension == ".pdf":
            text = extract_text_from_pdf(temp_path)
        else:
            with open(temp_path, "r", encoding="utf-8") as f:
                text = f.read()

        analysis = analyze_contract(text)

        return {"filename": file.filename, "analysis": analysis}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001)
