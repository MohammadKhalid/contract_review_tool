FROM python:3.11-slim

# Set cache locations so model downloads during build and runtime go to consistent paths
# (these are also used by the volumes in docker-compose)
ENV HF_HOME=/root/.cache/huggingface
ENV SPACY_DATA=/root/.spacy

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

# Model population (conditional download of the sentence-transformers model and
# spaCy "de_core_news_sm") is performed at *runtime* by docker-entrypoint.sh.
# It writes into HF_HOME / SPACY_DATA (backed by the named volumes for the prod
# profile or the .docker-cache bind mounts for the dev profile).
#
# The previous build-time --mount=type=bind steps (dev optimization) have been
# removed so that `docker compose --profile prod up -d --build` succeeds on a
# fresh git clone / new server without any host .docker-cache directories
# having to exist beforehand. BuildKit no longer needs to resolve those source
# paths at cache-key computation time.

# Copy application code
COPY . .

# Ensure the entrypoint script is executable (defensive for image builds)
RUN chmod +x docker-entrypoint.sh

EXPOSE 5001

# Run migrations via the entrypoint before starting the app.
# The entrypoint executes `alembic upgrade head` then starts uvicorn.
ENTRYPOINT ["./docker-entrypoint.sh"]
