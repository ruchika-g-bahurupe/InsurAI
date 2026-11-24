"""Persistent ChromaDB Vector Store for Insurance Knowledge Base."""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
except ImportError:  # pragma: no cover - handled gracefully when chromadb is missing
    chromadb = None  # type: ignore

from app.core.config import settings
from app.core.logging import logger
from app.rag.schemas import DocumentChunk


class VectorStoreError(RuntimeError):
    """Raised when ChromaDB storage or query operations fail."""


class ChromaVectorStore:
    """Manages persistent ChromaDB collection for insurance knowledge chunks."""

    COLLECTION_NAME = "insurance_knowledge"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
        self._client = None
        self._collection = None

    def _get_collection(self):
        if chromadb is None:
            raise VectorStoreError(
                "ChromaDB is not installed in the Python environment. Install chromadb to enable vector storage."
            )
        if self._collection is None:
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                f"ChromaDB collection '{self.COLLECTION_NAME}' ready at '{self.persist_directory}'."
            )
        return self._collection

    def upsert_chunks(
        self, chunks: List[DocumentChunk], embeddings: List[List[float]]
    ) -> int:
        """Upsert chunks and embeddings into ChromaDB (prevents duplicate chunk IDs)."""
        if len(chunks) != len(embeddings):
            raise VectorStoreError("Mismatch between chunk count and embedding vector count.")
        if not chunks:
            return 0

        collection = self._get_collection()
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "document_name": c.document_name,
                "category": c.category,
                "policy_type": c.policy_type or "",
                "page_number": int(c.page_number),
                "chunk_index": int(c.chunk_index),
            }
            for c in chunks
        ]
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(chunks)

    def delete_document_chunks(self, document_id: str) -> None:
        """Delete all vector chunks belonging to a specific document_id."""
        collection = self._get_collection()
        collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted ChromaDB vector chunks for document_id={document_id}")

    def get_document_chunk_ids(self, document_id: str) -> List[str]:
        """Return all existing ChromaDB chunk IDs for a document."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        raw = collection.get(where={"document_id": document_id}, include=[])
        return list(raw.get("ids") or [])

    def delete_chunk_ids(self, chunk_ids: List[str]) -> None:
        """Delete specific chunk IDs from ChromaDB."""
        if not chunk_ids:
            return
        collection = self._get_collection()
        collection.delete(ids=chunk_ids)

    def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run cosine similarity search with optional category, policy_type, and document_id filters."""
        collection = self._get_collection()
        total_count = collection.count()
        if total_count == 0:
            return []

        where_filter: Optional[Dict[str, Any]] = None
        conditions: List[Dict[str, Any]] = []
        if category:
            conditions.append({"category": category})
        if policy_type and policy_type.strip():
            conditions.append({"policy_type": policy_type.strip().upper()})
        if document_id:
            conditions.append({"document_id": document_id})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        n_results = min(max(1, top_k), total_count)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        raw = collection.query(**kwargs)
        ids_list = (raw.get("ids") or [[]])[0]
        docs_list = (raw.get("documents") or [[]])[0]
        metas_list = (raw.get("metadatas") or [[]])[0]
        dists_list = (raw.get("distances") or [[]])[0]

        results: List[Dict[str, Any]] = []
        for idx, chunk_id in enumerate(ids_list):
            distance = float(dists_list[idx]) if idx < len(dists_list) else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance))
            meta = metas_list[idx] if idx < len(metas_list) else {}
            results.append(
                {
                    "chunk_id": chunk_id,
                    "text": docs_list[idx] if idx < len(docs_list) else "",
                    "metadata": meta,
                    "distance": distance,
                    "similarity_score": round(similarity, 4),
                }
            )
        return results

    def get_document_chunks(self, document_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch stored chunks/excerpts for a specific document."""
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        raw = collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
            limit=limit,
        )
        ids_list = raw.get("ids") or []
        docs_list = raw.get("documents") or []
        metas_list = raw.get("metadatas") or []
        items = []
        for idx, chunk_id in enumerate(ids_list):
            meta = metas_list[idx] if idx < len(metas_list) else {}
            items.append(
                {
                    "chunk_id": chunk_id,
                    "page_number": meta.get("page_number", 1),
                    "chunk_index": meta.get("chunk_index", idx),
                    "excerpt": docs_list[idx] if idx < len(docs_list) else "",
                }
            )
        items.sort(key=lambda x: (x["page_number"], x["chunk_index"]))
        return items

    def total_chunks(self) -> int:
        """Return total vector records in the collection."""
        try:
            return self._get_collection().count()
        except Exception:
            return 0


vector_store = ChromaVectorStore()
