"""Gemini Embedding Service reusing the project's Google GenAI SDK client."""

import time
from typing import List, Optional
from google.genai import types
from app.agent.gemini_client import gemini_client
from app.core.config import settings
from app.core.logging import logger


class EmbeddingError(RuntimeError):
    """Raised when Gemini embedding generation fails after retries."""


class GeminiEmbeddingService:
    """Generates dense vector embeddings via the configured Google GenAI SDK."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        batch_size: int = 20,
        max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
    ):
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL
        self.batch_size = max(1, batch_size)
        self.max_retries = max(1, max_retries)
        self.base_backoff_seconds = base_backoff_seconds

    def is_available(self) -> bool:
        """Returns True if the Gemini client is live and configured."""
        return gemini_client.is_live() and gemini_client.client is not None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of document chunk texts."""
        if not texts:
            return []
        return self._embed_in_batches(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, query: str) -> List[float]:
        """Generate an embedding for a single search query."""
        cleaned = (query or "").strip()
        if not cleaned:
            raise EmbeddingError("Query text cannot be empty.")
        vectors = self._embed_in_batches([cleaned], task_type="RETRIEVAL_QUERY")
        if not vectors or not vectors[0]:
            raise EmbeddingError("Gemini returned an empty embedding vector for query.")
        return vectors[0]

    def _embed_in_batches(self, texts: List[str], task_type: str) -> List[List[float]]:
        if not self.is_available():
            raise EmbeddingError(
                "Gemini API is not configured (GEMINI_API_KEY missing or invalid). "
                "Cannot generate document embeddings."
            )

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_vectors = self._embed_batch_with_retry(batch, task_type=task_type)
            all_embeddings.extend(batch_vectors)
        return all_embeddings

    def _embed_batch_with_retry(self, batch: List[str], task_type: str) -> List[List[float]]:
        last_error: Optional[Exception] = None
        client = gemini_client.client
        if not client:
            raise EmbeddingError("Gemini client is not initialized.")

        for attempt in range(1, self.max_retries + 1):
            try:
                config = types.EmbedContentConfig(task_type=task_type)
                response = client.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                    config=config,
                )
                embeddings_obj = getattr(response, "embeddings", None) or []
                vectors = [list(e.values) for e in embeddings_obj if getattr(e, "values", None)]
                if len(vectors) != len(batch):
                    raise EmbeddingError(
                        f"Expected {len(batch)} embedding vectors, received {len(vectors)}."
                    )
                return vectors
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                is_retryable = any(
                    k in err_msg for k in ("429", "rate", "quota", "timeout", "503", "500", "unavailable")
                )
                logger.warning(
                    f"Embedding attempt {attempt}/{self.max_retries} failed ({self.model_name}): {e}"
                )
                if attempt < self.max_retries and is_retryable:
                    sleep_time = self.base_backoff_seconds * (2 ** (attempt - 1))
                    time.sleep(sleep_time)
                    continue
                break

        raise EmbeddingError(
            f"Failed to generate Gemini embeddings using '{self.model_name}': {last_error}"
        )


embedding_service = GeminiEmbeddingService()
