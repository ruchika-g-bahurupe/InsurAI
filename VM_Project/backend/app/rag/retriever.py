"""Semantic Retriever for Insurance Knowledge Base."""

from typing import List, Optional
from app.core.config import settings
from app.rag.embedding_service import GeminiEmbeddingService, embedding_service
from app.rag.schemas import RetrievedPassage
from app.rag.vector_store import ChromaVectorStore, vector_store


class KnowledgeRetriever:
    """Retrieves relevant insurance document passages above a relevance threshold."""

    def __init__(
        self,
        embedder: Optional[GeminiEmbeddingService] = None,
        store: Optional[ChromaVectorStore] = None,
        relevance_threshold: Optional[float] = None,
    ):
        self.embedder = embedder or embedding_service
        self.store = store or vector_store
        self.relevance_threshold = (
            relevance_threshold
            if relevance_threshold is not None
            else settings.RAG_RELEVANCE_THRESHOLD
        )

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        document_id: Optional[str] = None,
        relevance_threshold: Optional[float] = None,
    ) -> List[RetrievedPassage]:
        """
        Embed query, search ChromaDB, and return only passages meeting the relevance threshold.
        Does NOT pad with unrelated documents when fewer than top_k meet the threshold.
        """
        k = top_k if top_k is not None else settings.RAG_TOP_K
        threshold = (
            relevance_threshold
            if relevance_threshold is not None
            else self.relevance_threshold
        )

        query_vec = self.embedder.embed_query(query)
        raw_hits = self.store.similarity_search(
            query_embedding=query_vec,
            top_k=k,
            category=category,
            policy_type=policy_type,
            document_id=document_id,
        )

        passages: List[RetrievedPassage] = []
        for hit in raw_hits:
            score = float(hit.get("similarity_score", 0.0))
            if score < threshold:
                continue
            meta = hit.get("metadata") or {}
            passages.append(
                RetrievedPassage(
                    chunk_id=hit["chunk_id"],
                    document_id=str(meta.get("document_id", "")),
                    document_name=str(meta.get("document_name", "Unknown Document")),
                    category=str(meta.get("category", "")),
                    policy_type=meta.get("policy_type") or None,
                    page_number=int(meta.get("page_number", 1)),
                    relevant_excerpt=hit.get("text", ""),
                    similarity_score=score,
                )
            )

        return passages


knowledge_retriever = KnowledgeRetriever()
