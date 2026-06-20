# German Rental Contract Review Tool

An AI-powered application that analyzes German rental contracts (Mietverträge) to identify potentially invalid or problematic clauses using a legal knowledge base and NLP techniques.

## Features

- **Contract Analysis**: Upload PDF contracts for automated text extraction and analysis
- **OCR Support**: Automatic OCR fallback for scanned PDFs using Tesseract with German language support
- **Legal Knowledge Base**: Comprehensive German rental law database with vector search (BGB, BetrKV, BGH case law)
- **Invalid Clause Detection**: Identifies potentially unenforceable contract clauses with legal explanations
- **Semantic Search**: RAG-powered legal document retrieval for enhanced analysis

## Technologies Used

### Backend

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with pgvector extension for vector search
- **ORM**: SQLAlchemy
- **NLP**: spaCy (de_core_news_sm), sentence-transformers
- **OCR**: Tesseract OCR with German language support, pdf2image, Pillow
- **Validation**: Pydantic v2 + pydantic-settings for configuration

### Frontend

- Next.js (App Router) + TypeScript + Tailwind CSS
- next-intl for internationalization (English + German)

### Devops

- Docker, Docker Compose

### Testing

- pytest, pytest-asyncio, httpx (TestClient)

## Architecture

The backend follows a **clean layered architecture** with clear separation of concerns:

```
HTTP Request
    │
    ▼
┌──────────────┐
│   Routers    │  ← Thin HTTP layer: handles validation, routing, responses
│  (routers/)  │
└──────┬───────┘
       │ delegates to
       ▼
┌──────────────┐
│   Services   │  ← Business logic: PDF processing, NLP, issue detection, KB ops
│  (services/) │
└──────┬───────┘
       │ uses
       ▼
┌──────────────┐
│   Models /   │  ← Data layer: SQLAlchemy models, OCR utils, KB retrieval
│   Legal KB   │
│  (models/    │
│   legal_kb/  │
│   ocr_utils/ │
└──────────────┘
       │
       ▼
┌──────────────┐
│  Core / DI   │  ← Config, dependencies, exceptions, logging
│   (core/)    │
└──────────────┘
```

### Layer Responsibilities

| Layer        | Directory   | Responsibility                                                                                                                                       |
| ------------ | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Core**     | `core/`     | Application configuration (`config.py`), dependency injection (`dependencies.py`), custom exceptions (`exceptions.py`), logging setup (`logging.py`) |
| **Schemas**  | `schemas/`  | Pydantic request/response models for API validation and documentation                                                                                |
| **Services** | `services/` | Business logic — contract analysis pipeline, legal KB operations                                                                                     |
| **Routers**  | `routers/`  | Thin HTTP endpoints that delegate to services                                                                                                        |
| **Models**   | `models/`   | SQLAlchemy ORM models for database tables                                                                                                            |
| **Legal KB** | `legal_kb/` | Embedding generation, knowledge base ingestion, vector search retrieval                                                                              |
| **Tests**    | `tests/`    | Unit and integration tests                                                                                                                           |

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

   > **For active development** (with hot reload on Python + frontend), see the [Local Development](#local-development) section below instead.

4. **Seed the Legal Knowledge Base** (run after first startup):

   ```bash
   curl -X POST http://localhost:5001/legal-kb/seed
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5001
   - API Docs: http://localhost:5001/docs

## Database Migrations

This project uses **Alembic** for schema management (recommended for production and team development).

### How it works

- On container start, `docker-entrypoint.sh` automatically runs `alembic upgrade head` before launching the FastAPI app.
- The old `create_tables()` behavior (used during early development) is now opt-in via the environment variable `AUTO_CREATE_TABLES=true`.

### Common commands (inside Docker)

```bash
# Generate a new migration after changing a model
docker compose exec backend alembic revision --autogenerate -m "Add notes column to contracts"

# Apply pending migrations manually
docker compose --profile prod exec backend alembic upgrade head

# Check current migration state
docker compose exec backend alembic current
docker compose exec backend alembic history --verbose
```

### Adding AUTO_CREATE_TABLES (development escape hatch)

Add to your `.env` (or docker-compose environment) only when you want the legacy path:

```
AUTO_CREATE_TABLES=true
```

This is useful for quick throwaway experiments or certain CI jobs. Do not use it in production.

### Important notes

- The initial migration (`0001_initial_schema.py`) creates the `vector` extension and all six tables with the correct `ivfflat` indexes for pgvector.
- Always review autogenerated migrations, especially when they touch `Vector` columns or indexes.
- Seed data (`/legal-kb/seed`) is **application data**, not schema. Run it after migrations succeed.

## Local Development

This project supports a convenient development mode with hot reloading for both the backend (Python/FastAPI) and frontend (Next.js).

### Starting in Development Mode

Use the `dev` profile to enable hot reload on both services:

```bash
# Start everything with hot reload enabled (recommended for active development)
docker compose --profile dev up

# Start only the backend with Python hot reload
docker compose --profile dev up backend-dev

# Start only the frontend with Next.js hot reload
docker compose --profile dev up frontend-dev
```

### What the dev profile provides

| Service        | Hot Reload Behavior                              | Command Used |
|----------------|--------------------------------------------------|--------------|
| `backend-dev`  | Python code changes are picked up automatically | `uvicorn ... --reload --reload-dir .` |
| `frontend-dev` | Next.js Fast Refresh (instant UI updates)       | `npm run dev` |

### When to use what

| Command                                   | Recommended For                                      | Hot Reload |
|-------------------------------------------|------------------------------------------------------|------------|
| `docker compose up --build`               | Normal runs, testing "production-like" behavior      | No         |
| `docker compose --profile dev up`         | Active development (frequently editing Python/TSX)   | Yes        |
| `docker compose restart backend`          | After modifying Dockerfile, requirements.txt, etc.   | -          |

### Tips

- Database migrations still run automatically when `backend-dev` starts.
- The `dev` profile only activates the development variants (`backend-dev` + `frontend-dev`).
- Use the dev profile when working on:
  - Legal knowledge base seeding logic
  - Contract analysis improvements
  - New API endpoints
  - Frontend UI changes
- You can mix profiles if needed (e.g. keep the main `backend` running while using `frontend-dev`).

## Production Deployment
For a public server (VPS) with HTTPS, real Polar payments, and the full "Analyze for €2" flow:

See the detailed plan and exact commands in the session plan file (`.grok/.../plan.md` in your local checkout) or follow the high-level steps below.

1. On the server: `git clone`, `cp .env_template .env`, fill real production secrets (especially `POLAR_SERVER=production`, real product ID + token + webhook secret, `NEXT_PUBLIC_API_BASE_URL=https://yourdomain.com`, `CORS_ORIGINS=...`). For List[str] fields use JSON array syntax, e.g. `CORS_ORIGINS='["https://yourdomain.com"]'`. Plain string may work with our parser but JSON is guaranteed.
   The settings parser now flexibly accepts plain strings, JSON, or CSV for list fields.
2. One-time edits (already committed in this tree after the build-fix work):
   - `backend/Dockerfile` no longer requires host `.docker-cache` dirs at build time.
   - `frontend/Dockerfile` + compose now support build-time `NEXT_PUBLIC_API_BASE_URL`.
   - `nginx/` folder + service added for the reverse proxy.
3. `docker compose --profile prod up -d --build` (no manual `mkdir .docker-cache` needed).
4. On first start the backend entrypoint will download the ML models into the named volumes (visible in logs; only once).
5. Obtain Let's Encrypt certs with certbot, place in `nginx/certs/`, enable the 443 block in `nginx/nginx.conf`, restart nginx.
6. Register `https://yourdomain.com/api/webhook/polar` in the Polar production dashboard and seed the KB with your `ADMIN_API_KEY` via the public URL.
7. Visit https://yourdomain.com and test the complete Polar one-time purchase + analysis flow ("Analyze for €2", direct results page with loader, New Analysis reset).

The nginx proxy keeps the backend port internal. All browser calls and webhooks go through the single public domain.

### Accessing Swagger UI / API Docs on production
Once nginx is running (and after TLS if using HTTPS):

- Swagger UI: https://yourdomain.com/docs
- ReDoc: https://yourdomain.com/redoc

These are proxied to the backend. The page is public to view; authenticated calls (with `X-API-Key`) are supported in the "Try it out" feature. See `nginx/README.md` for details.

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

**Semantic Search:**

```bash
curl -X POST "http://localhost:5001/legal-kb/search?query=Kaution%20Rückzahlung"
```

**Check a Clause Against Invalid Patterns:**

```bash
curl -X POST "http://localhost:5001/legal-kb/check-clause?clause_text=Der%20Mieter%20leistet%20eine%20Kaution%20in%20Höhe%20von%20vier%20Monatsmieten."
```

## API Endpoints

### Contract Endpoints

| Method | Endpoint             | Description                       |
| ------ | -------------------- | --------------------------------- |
| POST   | `/contracts/analyze` | Upload and analyze a contract PDF |

### Legal Knowledge Base Endpoints

| Method | Endpoint                    | Description                                                    |
| ------ | --------------------------- | -------------------------------------------------------------- |
| POST   | `/legal-kb/seed`            | Initialize legal knowledge base with German rental law content |
| GET    | `/legal-kb/stats`           | Get statistics about the knowledge base                        |
| POST   | `/legal-kb/search`          | Semantic search over legal documents                           |
| GET    | `/legal-kb/invalid-clauses` | List known invalid clause patterns (filterable by topic/risk)  |
| POST   | `/legal-kb/check-clause`    | Check if a contract clause matches invalid patterns            |
| GET    | `/legal-kb/sources`         | List legal sources                                             |
| GET    | `/legal-kb/documents`       | Browse legal documents                                         |

## Authentication & Paywall (Polar.sh)

All API endpoints (except `/health`) now require a valid access token. There are two types:

- **Admin token** (`ADMIN_API_KEY`): Full access, including the admin-only `/legal-kb/seed` endpoint. Set in your `.env`.
- **User / Paying token**: A Polar.sh license key obtained after completing a one-time purchase via the embedded checkout in the frontend.

Regular users **cannot** call `/contracts/analyze` (or any other endpoint) until they complete payment.

### Quick Polar Setup (One-time Purchase + License Keys) — CRITICAL

**The #1 reason you get "Could not find a license key" after a successful checkout is that the product in Polar has no License Key benefit attached.**

1. Sign up at [polar.sh](https://polar.sh) (use Sandbox for testing).
2. In your org dashboard:
   - Create a **Product** (type: One-time) → e.g. "Contract Analysis Access Pass".
   - **Add a License Key benefit** to the product (this is mandatory).
     - Go to the product → Benefits tab → Add benefit → choose **License Keys**.
     - Configure prefix, usage limits, etc. as desired.
3. Go to Organization Settings → Access Tokens → create an Organization Access Token (OAT) with `license_keys:read` + `license_keys:write` scopes.
4. Copy the token + your Organization ID into `.env`.
5. Set `POLAR_ANALYSIS_PRODUCT_ID` to your product's ID.
6. (Required for automatic delivery) Create a Webhook in Polar pointing to your ngrok URL + `/api/webhook/polar` and copy the secret as `POLAR_WEBHOOK_SECRET`.
7. Start the app and test.

**If you skip step 2 (adding the License Key benefit), `licenseKeys.list` will always return 0 keys and the webhook will never deliver anything.**

### Troubleshooting: "No license key found" after successful purchase

If checkout succeeds but you always get 404 from `/api/polar/resolve-key`:

1. Go to the Polar dashboard and check the specific customer/order.
2. Confirm that a **License Key benefit** is attached to the product and that a key was actually generated.
3. Check that your `POLAR_WEBHOOK_SECRET` is correctly passed into the `frontend-dev` container (see docker-compose.yml).
4. Look for `[Polar Webhook]` logs when you complete a purchase or resend the event.

Only after the benefit is properly attached will the automatic flow work.

The frontend uses Polar's embedded checkout for a smooth experience (no full-page redirect). After success the key is resolved server-side and the user can immediately analyze.

> **Note on npm dependencies**: `@polar-sh/nextjs` currently declares a peer dependency on Next.js 15, while this project is still on Next 14.  
> We use `--legacy-peer-deps` when installing.  
> If you run `npm install` manually inside `frontend/`, use:
> ```bash
> cd frontend && npm install --legacy-peer-deps
> ```

### Using the API with a Token (curl examples)

**Admin (full access):**
```bash
curl -X POST "http://localhost:5001/contracts/analyze?lang=de" \
  -H "X-API-Key: $ADMIN_API_KEY" \
  -F "file=@contract.pdf"
```

**Paying user (after Polar purchase):**
```bash
curl -X POST "http://localhost:5001/contracts/analyze?lang=de" \
  -H "X-API-Key: POLAR-XXXX-YYYY-ZZZZ" \
  -F "file=@contract.pdf"
```

**Seed (admin only):**
```bash
curl -X POST "http://localhost:5001/legal-kb/seed?reset=false" \
  -H "X-API-Key: $ADMIN_API_KEY"
```

All other KB endpoints also require a valid key (admin or paying license).

### Environment Variables

See `.env_template` for the full Polar + admin section with comments.

Key vars:
- `ADMIN_API_KEY` – your long random admin secret
- `POLAR_ACCESS_TOKEN`, `POLAR_ORGANIZATION_ID`, `POLAR_SERVER=sandbox`
- `POLAR_ANALYSIS_PRODUCT_ID` (recommended)

### Testing the Paywall End-to-End (Sandbox)

1. Set `POLAR_SERVER=sandbox` + valid sandbox credentials + a test product with License Key benefit.
2. Load the frontend, select a PDF, click the buy button.
3. Complete checkout with Polar's test card (`4242 4242 4242 4242` etc.).
4. On success the license key appears, is auto-saved, and analysis works immediately.
5. Try calling the API without a key → you get 401/402.

Switch `POLAR_SERVER=production` and create a real product when you're ready to charge real money. Polar handles all tax compliance as Merchant of Record.

### Disabling / Local Development

- If you only ever use the admin key, you can leave Polar fields empty. The app will still require a token (the admin one).
- Never commit real Polar tokens or your `ADMIN_API_KEY`.

This design keeps the paywall enforcement on the backend while delivering a great frontend experience via Polar's excellent embedded checkout and license key delivery.

## Legal Knowledge Base

The application includes a comprehensive German rental law knowledge base with vector search capabilities:

### Features

- **Structured Legal Content**: BGB tenancy law sections, BetrKV operating cost regulations
- **Invalid Clause Database**: Common problematic contract clauses with explanations
- **Vector Search**: Semantic search using sentence-transformers embeddings
- **RAG Integration**: Contract analysis enhanced with legal knowledge retrieval
- **Regular Updates**: Quarterly updates to keep legal content current

### Sources

The knowledge base includes content from:

- **BGB (Bürgerliches Gesetzbuch)**: §§ 535–580a (tenancy law), § 551 (deposits), §§ 573–575 (termination), §§ 305–310 (AGB law)
- **BetrKV (Betriebskostenverordnung)**: Operating cost regulations
- **BGH Case Law**: Relevant court decisions on rental law
- **Invalid Clause Patterns**: Curated examples of unenforceable contract clauses

## Testing

The backend includes a comprehensive test suite with **48 tests** covering both business logic and API endpoints.

### Test Structure

```
backend/tests/
├── conftest.py                   # Shared fixtures and mock objects
├── test_contract_service.py      # 24 unit tests for contract analysis logic
├── test_legal_kb_service.py      # 11 unit tests for legal KB operations
├── test_routers_contracts.py     # 3 integration tests for contract endpoints
└── test_routers_legal_kb.py      # 10 integration tests for legal KB endpoints
```

### Running Tests

```bash
# Navigate to the backend directory
cd backend

# Install dependencies (including test dependencies)
pip install -r requirements.txt

# Run all tests with verbose output
python -m pytest tests/ -v --tb=short

# Run a specific test file
python -m pytest tests/test_contract_service.py -v

# Run tests matching a keyword
python -m pytest tests/ -k "validate_pdf"

# Run with coverage report
pip install pytest-cov
python -m pytest tests/ --cov=services --cov=routers --cov=core --cov-report=term-missing
```

### What's Tested

| Test File                   | Tests | Key Scenarios                                                                                                                          |
| --------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `test_contract_service.py`  | 24    | PDF validation, clause splitting, spaCy analysis, key term matching, entity extraction, legal issue detection, deduplication, file I/O |
| `test_legal_kb_service.py`  | 11    | Statistics, pattern filtering, clause checking, source/document retrieval, not-found handling                                          |
| `test_routers_contracts.py` | 3     | Successful analysis response format, non-PDF rejection, internal error handling                                                        |
| `test_routers_legal_kb.py`  | 10    | All 7 endpoints: seed, stats, search, invalid-clauses, check-clause, sources, documents                                                |

## Environment Configuration

Required environment variables (see `.env_template`):

| Variable            | Description                     |
| ------------------- | ------------------------------- |
| `POSTGRES_USER`     | Database username               |
| `POSTGRES_PASSWORD` | Database password               |
| `POSTGRES_DB`       | Database name                   |
| `DATABASE_URL`      | Full database connection string |

Optional configuration via environment variables (defaults in `backend/core/config.py`):

| Variable                      | Default                               | Description                          |
| ----------------------------- | ------------------------------------- | ------------------------------------ |
| `APP_TITLE`                   | German Rental Contract Review API     | Application name                     |
| `SPACY_MODEL`                 | de_core_news_sm                       | spaCy NLP model                      |
| `EMBEDDING_MODEL`             | paraphrase-multilingual-MiniLM-L12-v2 | Sentence transformer model           |
| `VECTOR_SIMILARITY_THRESHOLD` | 0.7                                   | Minimum similarity for vector search |
| `LOG_LEVEL`                   | INFO                                  | Logging level                        |
| `MAX_ISSUES`                  | 10                                    | Maximum legal issues to report       |

## Project Structure

```
contract_review_tool/
├── backend/
│   ├── app.py                   # FastAPI application entry point
│   ├── ocr_utils.py             # OCR and PDF processing utilities
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile
│   │
│   ├── core/                    # Core configuration & utilities
│   │   ├── config.py            # Pydantic-settings for environment variables
│   │   ├── dependencies.py      # FastAPI dependency injection (DB, NLP, embeddings)
│   │   ├── exceptions.py        # Custom exception hierarchy
│   │   └── logging.py           # Centralized logging setup
│   │
│   ├── schemas/                 # Pydantic request/response models
│   │   ├── contract.py          # Contract analysis schemas
│   │   └── legal_kb.py          # Legal KB schemas
│   │
│   ├── services/                # Business logic layer
│   │   ├── contract_service.py  # PDF processing, NLP, issue detection
│   │   └── legal_kb_service.py  # KB seeding, search, clause checking
│   │
│   ├── routers/                 # Thin API layer (delegates to services)
│   │   ├── contracts.py         # Contract analysis endpoints
│   │   └── legal_kb.py          # Legal KB endpoints
│   │
│   ├── database/
│   │   └── connection.py        # Database connection and setup
│   │
│   ├── models/
│   │   ├── contract.py          # Contract and analysis SQLAlchemy models
│   │   └── legal_kb.py          # Legal knowledge base SQLAlchemy models
│   │
│   ├── legal_kb/
│   │   ├── embeddings.py        # Vector embedding generation
│   │   ├── ingestion.py         # Knowledge base ingestion
│   │   ├── retrieval.py         # Semantic search and retrieval
│   │   └── seed_data.py         # Initial legal content
│   │
│   └── tests/                   # Test suite (48 tests)
│       ├── conftest.py          # Shared fixtures and mocks
│       ├── test_contract_service.py
│       ├── test_legal_kb_service.py
│       ├── test_routers_contracts.py
│       └── test_routers_legal_kb.py
│
├── frontend/
│   ├── src/                       # Next.js application
│   ├── messages/                  # i18n translations (en.json, de.json)
│   ├── public/
│   ├── package.json
│   ├── next.config.mjs
│   └── Dockerfile
│
├── docker-compose.yml
└── README.md
```

## Legal Notice

**This tool provides legal information for educational purposes. It is not a substitute for professional legal advice. Always consult with a qualified attorney for your specific situation.**
