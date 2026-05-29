FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for spaCy and OCR
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-deu \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Pre-download models to avoid runtime downloads
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copy application code
COPY . .

# Ensure the entrypoint script is executable (defensive for image builds)
RUN chmod +x docker-entrypoint.sh

EXPOSE 5001

# Run migrations via the entrypoint before starting the app.
# The entrypoint executes `alembic upgrade head` then starts uvicorn.
ENTRYPOINT ["./docker-entrypoint.sh"]
