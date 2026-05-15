## Technologies Used

- **Backend**: Python, FastAPI, SQLAlchemy, PostgreSQL, spaCy (German model), PyPDF2
- **OCR**: Tesseract OCR with German language support, pdf2image, Pillow
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Containerization**: Docker, Docker Compose
- **Database**: PostgreSQL with pgvector extension for vector search
- **NLP**: spaCy with de_core_news_sm model
- **Embeddings**: sentence-transformers for semantic search

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

### Legal KB API Endpoints

- `POST /legal-kb/seed` - Initialize legal knowledge base with German rental law content
- `GET /legal-kb/stats` - Get statistics about the knowledge base
- `POST /legal-kb/search` - Semantic search over legal documents
- `GET /legal-kb/invalid-clauses` - List known invalid clause patterns
- `POST /legal-kb/check-clause` - Check if a contract clause matches invalid patterns
- `GET /legal-kb/sources` - List legal sources
- `GET /legal-kb/documents` - Browse legal documents

### Sources

The knowledge base includes content from:

- **BGB (Bürgerliches Gesetzbuch)**: §§ 535–580a (tenancy law), § 551 (deposits), §§ 573–575 (termination), §§ 305–310 (AGB law)
- **BetrKV (Betriebskostenverordnung)**: Operating cost regulations
- **BGH Case Law**: Relevant court decisions on rental law
- **Invalid Clause Patterns**: Curated examples of unenforceable contract clauses

**Legal Notice**: This tool provides legal information for educational purposes. It is not a substitute for professional legal advice. Always consult with a qualified attorney for your specific situation.
