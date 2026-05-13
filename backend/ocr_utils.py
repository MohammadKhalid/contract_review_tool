import pytesseract
from PIL import Image
import PyPDF2
import io
import os
from pdf2image import convert_from_path
import tempfile


def has_text_content(pdf_path):
    """Check if PDF has extractable text content"""
    try:
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)

            # Check first few pages for text content
            for page_num in range(min(3, len(pdf_reader.pages))):
                page = pdf_reader.pages[page_num]
                text = page.extract_text().strip()

                # If we find substantial text content, assume it's text-based
                if len(text) > 100:  # More than 100 characters
                    return True

            return False
    except Exception as e:
        print(f"Error checking PDF text content: {e}")
        return False


def extract_text_with_ocr(pdf_path):
    """Extract text from scanned PDF using OCR"""
    try:
        # Convert PDF pages to images
        images = convert_from_path(pdf_path)

        extracted_text = ""
        for i, image in enumerate(images):
            # Convert PIL image to text using Tesseract OCR with German language
            text = pytesseract.image_to_string(image, lang="deu")
            extracted_text += f"\n--- Page {i+1} ---\n{text}"

        return extracted_text.strip()

    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return ""


def process_pdf_file(file_path):
    """
    Process PDF file - use direct text extraction if available,
    otherwise use OCR for scanned documents
    """
    if has_text_content(file_path):
        # Use direct text extraction for text-based PDFs
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text, "text_extraction"
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            # Fallback to OCR
            return extract_text_with_ocr(file_path), "ocr_fallback"
    else:
        # Use OCR for scanned PDFs
        return extract_text_with_ocr(file_path), "ocr"
