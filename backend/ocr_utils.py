"""
OCR utilities for PDF text extraction.
Uses PyMuPDF (fitz) for digital PDFs and Tesseract for scanned PDFs,
with German post-correction for improved OCR accuracy.
"""

import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import io
import os
from pdf2image import convert_from_path
import tempfile

from ocr_postprocess import correct_german_ocr


def has_text_content(pdf_path):
    """Check if PDF has extractable text content using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)

        # Check first few pages for text content
        for page_num in range(min(3, len(doc))):
            page = doc[page_num]
            text = page.get_text().strip()

            # If we find substantial text content, assume it's text-based
            if len(text) > 100:  # More than 100 characters
                doc.close()
                return True

        doc.close()
        return False
    except Exception as e:
        print(f"Error checking PDF text content: {e}")
        return False


def extract_text_with_ocr(pdf_path):
    """Extract text from scanned PDF using Tesseract OCR with German post-correction."""
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path)

        extracted_text = ""
        for i, image in enumerate(images):
            # Convert PIL image to text using Tesseract OCR with German language
            text = pytesseract.image_to_string(image, lang="deu")
            extracted_text += f"\n--- Page {i+1} ---\n{text}"

        # Apply German post-correction to fix common OCR errors
        corrected_text = correct_german_ocr(extracted_text.strip())

        return corrected_text

    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return ""


def extract_text_with_pymupdf(pdf_path):
    """Extract text from a digital PDF using PyMuPDF for better layout preservation.

    Note: Post-correction is NOT applied here since digital PDFs already have
    clean text. Correction is only needed for scanned PDF OCR output."""
    try:
        doc = fitz.open(pdf_path)
        extracted_text = ""
        for i, page in enumerate(doc):
            text = page.get_text()
            extracted_text += f"\n--- Page {i+1} ---\n{text}"
        doc.close()

        return extracted_text.strip()
    except Exception as e:
        print(f"Error extracting text with PyMuPDF: {e}")
        return ""


def process_pdf_file(file_path):
    """
    Process PDF file - use direct text extraction (PyMuPDF) if available,
    otherwise use OCR (Tesseract) for scanned documents.

    Returns:
        Tuple of (extracted_text, processing_method)
        processing_method: 'text_extraction', 'ocr', or 'ocr_fallback'
    """
    if has_text_content(file_path):
        # Use direct text extraction for text-based PDFs via PyMuPDF
        text = extract_text_with_pymupdf(file_path)
        if text:
            return text, "text_extraction"
        else:
            # Fallback to OCR if PyMuPDF extraction fails
            return extract_text_with_ocr(file_path), "ocr_fallback"
    else:
        # Use OCR for scanned PDFs
        return extract_text_with_ocr(file_path), "ocr"
