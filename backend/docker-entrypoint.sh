#!/bin/bash
set -e

# Ensure local cache directories exist on the host (Docker Compose creates
# bind mount sources, but we create them early for safety).
mkdir -p .docker-cache/huggingface .docker-cache/spacy

echo "=== Model pre-check (conditional download from volume) ==="

# --- Sentence Transformer model ---
echo "Checking SentenceTransformer model..."
python -c '
import os
from sentence_transformers import SentenceTransformer

model_name = "paraphrase-multilingual-MiniLM-L12-v2"
hf_home = os.environ.get("HF_HOME", "/root/.cache/huggingface")

# Check if model already exists in the cache/volume
safe_name = model_name.replace("/", "--")
model_dir = os.path.join(hf_home, "hub", f"models--{safe_name}")
if os.path.exists(model_dir):
    print(f"SentenceTransformer model \"{model_name}\" already present in volume/cache, skipping download.")
else:
    print(f"SentenceTransformer model \"{model_name}\" not found in volume. Downloading...")
    SentenceTransformer(model_name)
    print("SentenceTransformer model download complete.")
'

# --- spaCy model ---
echo "Checking spaCy model..."
python -c '
import subprocess
import spacy
import os

model_name = "de_core_news_sm"
spacy_data = os.environ.get("SPACY_DATA", "/root/.spacy")

# Check using spacy.load first (respects SPACY_DATA)
try:
    spacy.load(model_name)
    print(f"spaCy model \"{model_name}\" already present in volume/cache, skipping download.")
except OSError:
    print(f"spaCy model \"{model_name}\" not found in volume. Downloading into {spacy_data}...")
    subprocess.check_call(["python", "-m", "spacy", "download", model_name, "--direct"])
    print("spaCy model download complete.")
'
echo "=== Model checks complete ==="

echo "Waiting for database to be ready for migrations..."

# The compose healthcheck + depends_on should make the DB available,
# but we add a small retry loop for extra robustness (especially on slow CI or first boot).
for i in $(seq 1 30); do
    if alembic current >/dev/null 2>&1 || alembic upgrade head --sql >/dev/null 2>&1; then
        echo "Database is reachable."
        break
    fi
    echo "Database not ready yet (attempt $i/30)..."
    sleep 1
done

echo "Running Alembic migrations (upgrade head)..."
alembic upgrade head
echo "Migrations complete."

echo "Starting application..."
exec uvicorn app:app --host 0.0.0.0 --port 5001
