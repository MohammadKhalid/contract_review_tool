# German Rental Contract Review Tool

A comprehensive web application for analyzing German rental contracts using AI. The tool features OCR capabilities for scanned documents, intelligent text processing, and persistent data storage.

## Features

- **OCR Pipeline**: Automatically detects and processes scanned PDF documents using Tesseract OCR with German language support
- **Smart Text Extraction**: Intelligently chooses between direct text extraction and OCR based on document type
- **PDF and Text File Support**: Upload German rental contracts in PDF or text format
- **German Language Processing**: Uses spaCy with German language model for advanced text analysis
- **Key Term Detection**: Identifies important rental contract terms (Miete, Kaution, Kündigung, etc.)
- **Named Entity Recognition**: Extracts names, dates, addresses, and other entities from contracts
- **Basic Issue Detection**: Flags potential problems like excessive security deposits
- **PostgreSQL Database**: Persistent storage of all contracts and analysis results
- **Contract History**: View and manage previously analyzed contracts
- **Docker Containerization**: Easy deployment on any machine with full container orchestration

## Architecture

- **Backend**: Python FastAPI with spaCy for German NLP processing
- **Frontend**: Simple HTML/JavaScript interface for file upload and results display
- **Containerization**: Docker and Docker Compose for easy deployment

## Quick Start

### Prerequisites

- Docker and Docker Compose installed on your system

### Environment Setup

1. Copy the environment template:

   ```bash
   cp .env_template .env
   ```

2. Edit `.env` with your desired database credentials:

   ```bash
   # Database Configuration
   POSTGRES_DB=contract_db
   POSTGRES_USER=your_db_username
   POSTGRES_PASSWORD=your_secure_password

   # Application Environment
   ENV=development
   ```

### Running the Application

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd contract_review_tool
   ```

2. Start the application using Docker Compose:

   ```bash
   docker-compose up --build
   ```

3. Open your browser and navigate to:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5001

### Usage

1. Open the frontend at http://localhost:3000
2. Click "Choose File" and select a German rental contract (PDF or text file)
3. Click "Analyze Contract" to process the document
4. View the analysis results including:
   - Basic statistics (word count, sentences)
   - Key rental terms found
   - Named entities extracted
   - Potential issues detected

## Development

### Backend Development

The backend is built with FastAPI and uses spaCy for German text processing. To run locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 5001
```

### Frontend Development

The frontend is a simple static HTML/JavaScript application. To run locally:

```bash
cd frontend
# Serve with any static file server, e.g., using Python:
python -m http.server 8000
```

## OCR Pipeline

The application includes an intelligent OCR pipeline that can handle both text-based and scanned PDF documents:

1. **Document Type Detection**: Automatically detects if a PDF contains extractable text
2. **Smart Processing**:
   - **Text PDFs**: Direct text extraction using PyPDF2 (faster, more accurate)
   - **Scanned PDFs**: OCR processing using Tesseract with German language support
   - **Fallback**: If direct extraction fails, automatically falls back to OCR
3. **German Language Support**: OCR is optimized for German text recognition

## Database Schema

The application uses PostgreSQL to store all contract data and analysis results:

### Tables

- **contracts**: Stores contract metadata
  - `id`, `filename`, `file_path`, `file_size`, `mime_type`, `upload_date`, `processing_method`

- **contract_analyses**: Stores analysis results for each contract
  - `id`, `contract_id`, `analysis_date`, `extracted_text`, `word_count`, `sentence_count`
  - `key_terms` (JSON), `named_entities` (JSON), `potential_issues` (JSON)
  - `processing_time_seconds`, `ocr_used`

## API Endpoints

### Core Endpoints

- `GET /health` - Health check endpoint
- `POST /analyze` - Analyze uploaded contract file
  - Accepts: `multipart/form-data` with `file` field
  - Supports: PDF and TXT files
  - Features: Automatic OCR for scanned PDFs
  - Returns: JSON with analysis results, processing metadata, and database ID

### Contract Management

- `GET /contracts` - List analyzed contracts
  - Query parameters: `skip`, `limit` for pagination
  - Returns: List of contracts with latest analysis summary

- `GET /contracts/{contract_id}` - Get detailed contract information
  - Returns: Full contract details with all analyses and extracted text preview

## Technologies Used

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, spaCy (German model), PyPDF2
- **OCR**: Tesseract OCR with German language support, pdf2image, Pillow
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL with SQLAlchemy ORM
- **NLP**: spaCy with de_core_news_sm model

## Future Enhancements

- Advanced contract clause analysis
- Legal compliance checking
- Multi-language support
- User authentication and contract history
- Integration with legal databases
