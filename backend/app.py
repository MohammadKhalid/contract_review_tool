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
from routers.legal_kb import router as legal_kb_router
from routers.contracts import router as contracts_router

app = FastAPI(title="German Rental Contract Review API")


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    create_tables()


# Include legal knowledge base router
app.include_router(legal_kb_router)

# Include contracts router
app.include_router(contracts_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
