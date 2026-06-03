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

# Pre-download models (dev-optimized).
#
# In the dev profile we use local bind mounts (see docker-compose.yml).
# By using --mount=type=bind here, `docker compose up --build` can see
# models that were previously downloaded into .docker-cache/ on the host.
#
# This significantly reduces re-downloads on rebuilds for developers.

# Sentence Transformer model (Hugging Face cache)
RUN --mount=type=bind,source=./.docker-cache/huggingface,target=/root/.cache/huggingface \
    <<'EOF'
python -c '
import os
from sentence_transformers import SentenceTransformer
model_name = "paraphrase-multilingual-MiniLM-L12-v2"
cache_dir = os.environ.get("HF_HOME", "/root/.cache/huggingface")
model_path = os.path.join(cache_dir, "hub", "models--" + model_name.replace("/", "--"))
if os.path.exists(model_path):
    print(f"SentenceTransformer model {model_name} already present (from host bind mount), skipping download.")
else:
    print(f"Downloading SentenceTransformer model {model_name} into host bind mount...")
    SentenceTransformer(model_name)
    print("Download complete.")
'
EOF

# spaCy model
RUN --mount=type=bind,source=./.docker-cache/spacy,target=/root/.spacy \
    <<'EOF'
python -c '
import subprocess
import spacy
model_name = "de_core_news_sm"
try:
    spacy.load(model_name)
    print(f"spaCy model {model_name} already present (from host bind mount), skipping download.")
except OSError:
    print(f"Downloading spaCy model {model_name} into host bind mount...")
    subprocess.check_call(["python", "-m", "spacy", "download", model_name, "--direct"])
    print("Download complete.")
'
EOF

# Copy application code
COPY . .

# Ensure the entrypoint script is executable (defensive for image builds)
RUN chmod +x docker-entrypoint.sh

EXPOSE 5001

# Run migrations via the entrypoint before starting the app.
# The entrypoint executes `alembic upgrade head` then starts uvicorn.
ENTRYPOINT ["./docker-entrypoint.sh"]
