"""
Embedding service for legal knowledge base.
Handles text embeddings using sentence-transformers for vector search.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union, Dict, Tuple
import logging
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.
    Uses a multilingual model optimized for German legal text.
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize the embedding service.

        Args:
            model_name: HuggingFace model name for sentence transformers
        """
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            self._embedding_cache: Dict[str, np.ndarray] = {}
            logger.info(
                f"Loaded embedding model: {model_name} (dimension: {self.embedding_dim})"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}")
            raise

    def encode_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text (with simple LRU cache).
        """
        if not text or not text.strip():
            return np.zeros(self.embedding_dim, dtype=np.float32)

        # Simple cache key
        key = hashlib.md5(text.encode("utf-8")).hexdigest()

        if key in self._embedding_cache:
            return self._embedding_cache[key]

        try:
            embedding = self.model.encode(
                text, convert_to_numpy=True, normalize_embeddings=True
            ).astype(np.float32)

            # Very small bounded cache (last 512 unique clauses)
            if len(self._embedding_cache) > 512:
                self._embedding_cache.pop(next(iter(self._embedding_cache)))

            self._embedding_cache[key] = embedding
            return embedding
        except Exception as e:
            logger.error(f"Error encoding text: {e}")
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts to embed

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)

        # Filter out empty texts
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

        try:
            embeddings = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,
            )

            # Reconstruct full array with zeros for empty texts
            result = np.zeros((len(texts), self.embedding_dim), dtype=np.float32)
            valid_indices = [i for i, text in enumerate(texts) if text and text.strip()]

            for i, embedding in enumerate(embeddings):
                result[valid_indices[i]] = embedding.astype(np.float32)

            return result

        except Exception as e:
            logger.error(f"Error encoding batch: {e}")
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

    def get_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Cosine similarity for normalized embeddings is just dot product
            similarity = np.dot(embedding1, embedding2)

            # Ensure result is in [0, 1] range (due to floating point precision)
            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def get_similarities(
        self, query_embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarities between query embedding and multiple embeddings.

        Args:
            query_embedding: Query embedding vector
            embeddings: Array of embedding vectors to compare against

        Returns:
            Array of similarity scores
        """
        try:
            # For normalized embeddings, cosine similarity is just matrix multiplication
            similarities = np.dot(embeddings, query_embedding)

            # Clip to [0, 1] range
            return np.clip(similarities, 0.0, 1.0)

        except Exception as e:
            logger.error(f"Error calculating similarities: {e}")
            return np.zeros(len(embeddings), dtype=np.float32)


# Global instance for reuse
embedding_service = EmbeddingService()
