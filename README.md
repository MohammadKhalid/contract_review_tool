# German Rental Contract Review Tool

An AI-powered application that analyzes German rental contracts (Mietverträge) to identify potentially invalid or problematic clauses using legal knowledge base and NLP techniques.

## Features

- **Contract Analysis**: Upload PDF contracts for automated text extraction and analysis
- **OCR Support**: Automatic OCR fallback for scanned PDFs using Tesseract with German language support
- **Legal Knowledge Base**: Comprehensive German rental law database with vector search (BGB, BetrKV, BGH case law)
- **Invalid Clause Detection**: Identifies potentially unenforceable contract clauses with legal explanations
- **Semantic Search**: RAG-powered legal document retrieval for enhanced analysis

## Technologies Used

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, spaCy (German model), PyPDF2
- **OCR**: Tesseract OCR with German language support, pdf2image, Pillow
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL with pgvector extension for vector search
- **NLP**: spaCy with de_core_news_sm model
- **Embeddings**: sentence-transformers for semantic search

## Installation & Setup

### Prerequisites

- Docker and Docker Compose installed
- Git

### Quick Start

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd contract_review_tool
   ```

2. **Configure environment variables**:

   ```bash
   cp .env_template .env
   # Edit .env with your configuration
   ```

3. **Start the application**:

   ```bash
   docker-compose up --build
   ```

4. **Seed the Legal Knowledge Base** (run after first startup):

   ```bash
   curl -X POST http://localhost:5001/legal-kb/seed
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5001
   - API Docs: http://localhost:5001/docs

## Usage

### Web Interface

1. Open http://localhost:3000 in your browser
2. Click "Choose File" and select a German rental contract (PDF or TXT)
3. Click "Analyze Contract"
4. View the analysis results including:
   - Basic statistics (word count, sentences)
   - Key terms detected
   - Named entities
   - Potential legal issues with explanations

### API Usage

**Analyze a Contract:**

```bash
curl -X POST http://localhost:5001/contracts/analyze \
  -F "file=@contract.pdf"
```

**Check Knowledge Base Stats:**

```bash
curl http://localhost:5001/legal-kb/stats
```

## API Endpoints

### Contract Endpoints

- `POST /contracts/analyze` - Upload and analyze a contract PDF

### Legal Knowledge Base Endpoints

- `POST /legal-kb/seed` - Initialize legal knowledge base with German rental law content
- `GET /legal-kb/stats` - Get statistics about the knowledge base
- `POST /legal-kb/search` - Semantic search over legal documents
- `GET /legal-kb/invalid-clauses` - List known invalid clause patterns
- `POST /legal-kb/check-clause` - Check if a contract clause matches invalid patterns
- `GET /legal-kb/sources` - List legal sources
- `GET /legal-kb/documents` - Browse legal documents

## Legal Knowledge Base

The application includes a comprehensive German rental law knowledge base with vector search capabilities:

### Features

- **Structured Legal Content**: BGB tenancy law sections, BetrKV operating cost regulations
- **Invalid Clause Database**: Common problematic contract clauses with explanations
- **Vector Search**: Semantic search using sentence-transformers embeddings
- **RAG Integration**: Contract analysis enhanced with legal knowledge retrieval
- **Regular Updates**: Quarterly updates to keep legal content current

### Setup

1. **Seed the Knowledge Base** (run after first startup):

   ```bash
   curl -X POST http://localhost:5001/legal-kb/seed
   ```

2. **Check Knowledge Base Stats**:

   ```bash
   curl http://localhost:5001/legal-kb/stats
   ```

### Sources

The knowledge base includes content from:

- **BGB (Bürgerliches Gesetzbuch)**: §§ 535–580a (tenancy law), § 551 (deposits), §§ 573–575 (termination), §§ 305–310 (AGB law)
- **BetrKV (Betriebskostenverordnung)**: Operating cost regulations
- **BGH Case Law**: Relevant court decisions on rental law
- **Invalid Clause Patterns**: Curated examples of unenforceable contract clauses

## Environment Configuration

Required environment variables (see `.env_template`):

- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `DATABASE_URL` - Full database connection string

## Project Structure

```
contract_review_tool/
├── backend/
│   ├── app.py                 # FastAPI application entry point
│   ├── ocr_utils.py           # OCR and PDF processing utilities
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile
│   ├── database/
│   │   └── connection.py      # Database connection and setup
│   ├── models/
│   │   ├── contract.py        # Contract and analysis models
│   │   └── legal_kb.py        # Legal knowledge base models
│   ├── legal_kb/
│   │   ├── embeddings.py      # Vector embeddings
│   │   ├── ingestion.py       # Knowledge base ingestion
│   │   ├── retrieval.py       # Semantic search and retrieval
│   │   └── seed_data.py       # Initial legal content
│   └── routers/
│       ├── contracts.py       # Contract analysis endpoints
│       └── legal_kb.py        # Legal KB endpoints
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── style.css
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Legal Notice

**This tool provides legal information for educational purposes. It is not a substitute for professional legal advice. Always consult with a qualified attorney for your specific situation.**
