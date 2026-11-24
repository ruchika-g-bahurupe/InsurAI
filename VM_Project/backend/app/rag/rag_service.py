"""Centralized RAG Service coordinating PDF ingestion, indexing, retrieval, and grounded Q&A."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.gemini_client import gemini_client
from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.core.logging import logger
from app.db.models.knowledge_document import KnowledgeDocument
from app.rag.document_loader import (
    DocumentExtractionError,
    DocumentValidationError,
    extract_pdf_pages,
    save_pdf_securely,
    validate_pdf_upload,
)
from app.rag.embedding_service import EmbeddingError, GeminiEmbeddingService, embedding_service
from app.rag.retriever import KnowledgeRetriever, knowledge_retriever
from app.rag.schemas import (
    DocumentCategory,
    DocumentUploadResponse,
    KnowledgeAskResponse,
    KnowledgeBaseStatsResponse,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchResponse,
    ProcessingStatus,
    RetrievedPassage,
    SourceCitation,
)
from app.rag.text_chunker import TextChunker
from app.rag.vector_store import ChromaVectorStore, VectorStoreError, vector_store


GROUNDED_RAG_SYSTEM_PROMPT = """You are an Insurance Policy & Guidelines Knowledge Assistant for InsureDesk AI.

STRICT GROUNDING RULES:
1. Answer ONLY using the retrieved document passages provided below.
2. NEVER invent policy clauses, coverage limits, exclusions, waiting periods, or legal terms.
3. Cite exact document names and page numbers for every factual claim (e.g., [Motor_Policy_Wording.pdf, Page 4]).
4. If the retrieved passages do NOT contain enough information to answer the question, explicitly state that the available knowledge base documents do not contain sufficient evidence to answer.
5. If retrieved passages contain conflicting statements across documents or pages, explicitly point out both statements with their respective document names and page numbers instead of silently choosing one.
6. NEVER make definitive claim approval or rejection decisions; explain what the policy wording or guidelines state and note that final claim decisions require authorized adjuster/employee review.
"""


class RAGService:
    """Coordinates PDF extraction, chunking, embeddings, ChromaDB storage, retrieval, and grounded Q&A."""

    def __init__(
        self,
        chunker: Optional[TextChunker] = None,
        embedder: Optional[GeminiEmbeddingService] = None,
        store: Optional[ChromaVectorStore] = None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.chunker = chunker or TextChunker()
        self.embedder = embedder or embedding_service
        self.store = store or vector_store
        self.retriever = retriever or knowledge_retriever

    def upload_document(
        self,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
        category: str,
        policy_type: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> DocumentUploadResponse:
        """Validate, deduplicate, persist, and process an uploaded insurance PDF."""
        valid_categories = {c.value for c in DocumentCategory}
        if category not in valid_categories:
            raise DocumentValidationError(
                f"Unsupported document category '{category}'. "
                f"Allowed categories: {', '.join(sorted(valid_categories))}"
            )

        safe_name, file_hash = validate_pdf_upload(
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
        )

        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            # Duplicate detection via SHA-256 file hash
            existing = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.file_hash == file_hash)
            ).scalars().first()

            if existing:
                hint = (
                    " Click Reindex in the Document Library to retry processing."
                    if existing.processing_status == ProcessingStatus.FAILED.value
                    else ""
                )
                return DocumentUploadResponse(
                    document=KnowledgeDocumentResponse.model_validate(existing),
                    is_duplicate=True,
                    message=(
                        f"Duplicate PDF detected: '{existing.document_name}' "
                        f"(status: {existing.processing_status}) has already been uploaded.{hint}"
                    ),
                )

            doc_id, stored_path = save_pdf_securely(file_bytes)
            doc_record = KnowledgeDocument(
                id=doc_id,
                document_name=safe_name,
                category=category,
                policy_type=policy_type.strip().upper() if policy_type and policy_type.strip() else None,
                file_hash=file_hash,
                file_location=stored_path,
                file_size_bytes=len(file_bytes),
                processing_status=ProcessingStatus.UPLOADED.value,
                page_count=0,
                chunk_count=0,
                upload_timestamp=datetime.now(timezone.utc),
            )
            session.add(doc_record)
            session.commit()
            session.refresh(doc_record)

            # Process synchronously through extraction -> chunking -> embeddings -> indexing
            processed = self.process_document(doc_record.id, db=session)
            msg = (
                "Document uploaded and indexed successfully."
                if processed.processing_status == ProcessingStatus.COMPLETED.value
                else f"Document uploaded, but processing failed: {processed.error_message}"
            )
            return DocumentUploadResponse(
                document=processed,
                is_duplicate=False,
                message=msg,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            if owns_session:
                session.close()

    def process_document(
        self, document_id: str, db: Optional[Session] = None
    ) -> KnowledgeDocumentResponse:
        """Execute PDF extraction -> chunking -> embedding -> ChromaDB indexing with status tracking."""
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            doc = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            ).scalars().first()
            if not doc:
                raise ValueError(f"Knowledge document '{document_id}' not found.")

            def _set_status(status: ProcessingStatus, error: Optional[str] = None) -> None:
                doc.processing_status = status.value
                doc.error_message = error
                session.commit()
                session.refresh(doc)

            try:
                # Stage 1: Extracting Text
                _set_status(ProcessingStatus.EXTRACTING_TEXT)
                page_count, pages = extract_pdf_pages(doc.file_location)
                doc.page_count = page_count

                # Stage 2: Chunking
                _set_status(ProcessingStatus.CHUNKING)
                chunks = self.chunker.chunk_pages(
                    pages=pages,
                    document_id=doc.id,
                    document_name=doc.document_name,
                    category=doc.category,
                    policy_type=doc.policy_type,
                )
                if not chunks:
                    raise DocumentExtractionError(
                        "Text extraction succeeded, but no valid non-empty chunks could be generated."
                    )

                # Stage 3: Generating Embeddings
                _set_status(ProcessingStatus.GENERATING_EMBEDDINGS)
                embeddings = self.embedder.embed_documents([c.text for c in chunks])

                # Stage 4: Indexing in ChromaDB (safe upsert + obsolete chunk cleanup)
                _set_status(ProcessingStatus.INDEXING)
                existing_ids = set(self.store.get_document_chunk_ids(doc.id))
                new_ids = {c.chunk_id for c in chunks}
                indexed_count = self.store.upsert_chunks(chunks, embeddings)
                obsolete_ids = list(existing_ids - new_ids)
                if obsolete_ids:
                    self.store.delete_chunk_ids(obsolete_ids)

                doc.chunk_count = indexed_count
                doc.processing_status = ProcessingStatus.COMPLETED.value
                doc.error_message = None
                doc.last_indexed_timestamp = datetime.now(timezone.utc)
                session.commit()
                session.refresh(doc)

                logger.info(
                    f"Indexed KnowledgeDocument '{doc.document_name}' ({doc.id}): "
                    f"{doc.page_count} pages, {doc.chunk_count} chunks."
                )
                return KnowledgeDocumentResponse.model_validate(doc)

            except (DocumentExtractionError, EmbeddingError, VectorStoreError) as known_err:
                logger.error(f"Processing failed for document '{doc.id}': {known_err}")
                _set_status(ProcessingStatus.FAILED, error=str(known_err))
                return KnowledgeDocumentResponse.model_validate(doc)
            except Exception as unexpected_err:
                logger.exception(f"Unexpected processing error for document '{doc.id}': {unexpected_err}")
                _set_status(
                    ProcessingStatus.FAILED,
                    error=f"Unexpected processing error: {str(unexpected_err)}",
                )
                return KnowledgeDocumentResponse.model_validate(doc)
        finally:
            if owns_session:
                session.close()

    def reindex_document(
        self, document_id: str, db: Optional[Session] = None
    ) -> KnowledgeDocumentResponse:
        """
        Safely reindex an existing document without deleting searchable vectors upfront.
        Existing vectors are preserved if PDF extraction or Gemini embedding fails.
        """
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            doc = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            ).scalars().first()
            if not doc:
                raise ValueError(f"Knowledge document '{document_id}' not found.")

            return self.process_document(document_id=document_id, db=session)
        finally:
            if owns_session:
                session.close()

    def delete_document(
        self, document_id: str, db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Safely delete a knowledge document:
        1. Delete associated vectors from ChromaDB first (fail-safe against orphaned vectors).
        2. Remove PDF file from disk.
        3. Delete metadata record from SQLite (never touching customer/policy records).
        """
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            doc = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            ).scalars().first()
            if not doc:
                raise ValueError(f"Knowledge document '{document_id}' not found.")

            # Step 1: Delete ChromaDB vectors
            try:
                self.store.delete_document_chunks(document_id)
            except VectorStoreError as e:
                logger.error(f"Failed deleting vectors for '{document_id}': {e}")
                raise VectorStoreError(
                    f"Aborted deletion to prevent orphaned vector records: {e}"
                )

            # Step 2: Remove physical PDF file if present (abort metadata deletion if file removal fails)
            file_removed = False
            if doc.file_location and os.path.exists(doc.file_location):
                try:
                    Path(doc.file_location).unlink()
                    file_removed = True
                except OSError as oe:
                    err_msg = (
                        f"ChromaDB vectors were removed, but failed to delete PDF file "
                        f"'{doc.document_name}': {oe}. Metadata preserved for retry."
                    )
                    logger.error(err_msg)
                    doc.error_message = err_msg
                    session.commit()
                    raise RuntimeError(err_msg) from oe

            # Step 3: Remove SQLite metadata row
            doc_name = doc.document_name
            session.delete(doc)
            session.commit()

            return {
                "deleted": True,
                "document_id": document_id,
                "document_name": doc_name,
                "file_removed": file_removed,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            if owns_session:
                session.close()

    def get_document_status(
        self, document_id: str, db: Optional[Session] = None
    ) -> KnowledgeDocumentDetailResponse:
        """Retrieve document metadata, status, and indexed excerpts."""
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            doc = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            ).scalars().first()
            if not doc:
                raise ValueError(f"Knowledge document '{document_id}' not found.")

            excerpts: List[Dict[str, Any]] = []
            if doc.processing_status == ProcessingStatus.COMPLETED.value:
                try:
                    excerpts = self.store.get_document_chunks(document_id, limit=12)
                except Exception as e:
                    logger.warning(f"Could not load excerpts for {document_id}: {e}")

            base_data = KnowledgeDocumentResponse.model_validate(doc).model_dump()
            return KnowledgeDocumentDetailResponse(**base_data, excerpts=excerpts)
        finally:
            if owns_session:
                session.close()

    def get_document_file_info(
        self, document_id: str, db: Optional[Session] = None
    ) -> Dict[str, str]:
        """Return safe file path and display name for viewing an uploaded PDF."""
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            doc = session.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
            ).scalars().first()
            if not doc:
                raise ValueError(f"Knowledge document '{document_id}' not found.")
            upload_root = Path(settings.RAG_UPLOAD_DIR).resolve()
            file_path = Path(doc.file_location).resolve()
            if not str(file_path).startswith(str(upload_root)) or not file_path.is_file():
                raise FileNotFoundError(f"Stored PDF file for '{doc.document_name}' was not found on disk.")
            return {"file_path": str(file_path), "document_name": doc.document_name}
        finally:
            if owns_session:
                session.close()

    def list_documents(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> List[KnowledgeDocumentResponse]:
        """List all uploaded knowledge base documents ordered by upload timestamp desc."""
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            stmt = select(KnowledgeDocument).order_by(KnowledgeDocument.upload_timestamp.desc())
            if category:
                stmt = stmt.where(KnowledgeDocument.category == category)
            if status:
                stmt = stmt.where(KnowledgeDocument.processing_status == status)
            docs = session.execute(stmt).scalars().all()
            return [KnowledgeDocumentResponse.model_validate(d) for d in docs]
        finally:
            if owns_session:
                session.close()

    def get_stats(self, db: Optional[Session] = None) -> KnowledgeBaseStatsResponse:
        """Return real-time Knowledge Base counts from SQLite."""
        owns_session = db is None
        session = db or SyncSessionLocal()
        try:
            docs = session.execute(select(KnowledgeDocument)).scalars().all()
            total_documents = len(docs)
            indexed_documents = sum(
                1 for d in docs if d.processing_status == ProcessingStatus.COMPLETED.value
            )
            failed_documents = sum(
                1 for d in docs if d.processing_status == ProcessingStatus.FAILED.value
            )
            processing_statuses = {
                ProcessingStatus.UPLOADED.value,
                ProcessingStatus.EXTRACTING_TEXT.value,
                ProcessingStatus.CHUNKING.value,
                ProcessingStatus.GENERATING_EMBEDDINGS.value,
                ProcessingStatus.INDEXING.value,
            }
            processing_documents = sum(
                1 for d in docs if d.processing_status in processing_statuses
            )
            total_chunks = sum(
                d.chunk_count
                for d in docs
                if d.processing_status == ProcessingStatus.COMPLETED.value
            )
            categories_breakdown: Dict[str, int] = {}
            for d in docs:
                categories_breakdown[d.category] = categories_breakdown.get(d.category, 0) + 1

            return KnowledgeBaseStatsResponse(
                total_documents=total_documents,
                indexed_documents=indexed_documents,
                processing_documents=processing_documents,
                failed_documents=failed_documents,
                total_chunks=total_chunks,
                categories_breakdown=categories_breakdown,
            )
        finally:
            if owns_session:
                session.close()

    def retrieve_relevant_chunks(
        self,
        query: str,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        document_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[RetrievedPassage]:
        """Retrieve relevant passages from ChromaDB."""
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            category=category,
            policy_type=policy_type,
            document_id=document_id,
        )

    def search_documents(
        self,
        query: str,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        document_id: Optional[str] = None,
        top_k: int = 5,
    ) -> KnowledgeSearchResponse:
        """Semantic search returning structured passages."""
        passages = self.retrieve_relevant_chunks(
            query=query,
            category=category,
            policy_type=policy_type,
            document_id=document_id,
            top_k=top_k,
        )
        return KnowledgeSearchResponse(
            query=query,
            total_results=len(passages),
            passages=passages,
        )

    def ask_question(
        self,
        question: str,
        category: Optional[str] = None,
        policy_type: Optional[str] = None,
        document_id: Optional[str] = None,
        top_k: int = 5,
    ) -> KnowledgeAskResponse:
        """
        Retrieve relevant passages and generate a strictly grounded answer using Gemini.
        Handles insufficient evidence, conflicting statements, and Gemini API failures gracefully.
        """
        passages = self.retrieve_relevant_chunks(
            query=question,
            category=category,
            policy_type=policy_type,
            document_id=document_id,
            top_k=top_k,
        )

        sources = [
            SourceCitation(
                document_id=p.document_id,
                document_name=p.document_name,
                category=p.category,
                page_number=p.page_number,
                relevant_excerpt=p.relevant_excerpt,
                retrieval_similarity=p.similarity_score,
            )
            for p in passages
        ]

        if not passages:
            return KnowledgeAskResponse(
                question=question,
                answer=(
                    "Insufficient evidence: No relevant passages were found in the indexed insurance "
                    "knowledge base documents for this question. Try uploading relevant policy or "
                    "guideline PDFs, or rephrasing your query."
                ),
                sources=[],
                insufficient_evidence=True,
                retrieval_note="0 passages met the configured semantic relevance threshold.",
                model_used=None,
            )

        context_blocks = []
        for idx, p in enumerate(passages, start=1):
            context_blocks.append(
                f"[Passage {idx}]\n"
                f"Document: {p.document_name}\n"
                f"Category: {p.category}\n"
                f"Page: {p.page_number}\n"
                f"Content:\n{p.relevant_excerpt}"
            )

        prompt = (
            f"Employee Question:\n{question}\n\n"
            f"Retrieved Insurance Knowledge Passages:\n\n"
            + "\n\n---\n\n".join(context_blocks)
            + "\n\nProvide a clear, grounded answer citing document names and page numbers. "
            "If the passages do not fully answer the question or contain conflicting statements, "
            "state that explicitly."
        )

        if not gemini_client.is_live():
            return KnowledgeAskResponse(
                question=question,
                answer=(
                    "Gemini LLM is currently in offline/degraded mode (GEMINI_API_KEY not configured). "
                    "Review the retrieved source passages below directly."
                ),
                sources=sources,
                insufficient_evidence=False,
                retrieval_note="Retrieved passages are shown without LLM synthesis.",
                model_used=None,
            )

        answer_text = gemini_client.generate_structured_analysis(
            system_instruction=GROUNDED_RAG_SYSTEM_PROMPT,
            prompt=prompt,
            response_schema=None,
            use_analysis_model=False,
            timeout_seconds=30.0,
        )

        if not answer_text:
            return KnowledgeAskResponse(
                question=question,
                answer=(
                    "Unable to generate a synthesized answer because the Gemini generation service "
                    "timed out or returned an error. The retrieved source passages are provided below."
                ),
                sources=sources,
                insufficient_evidence=False,
                retrieval_note="Gemini generation failed; raw retrieved passages preserved.",
                model_used=settings.GEMINI_MODEL,
            )

        lower_ans = answer_text.lower()
        insufficient = any(
            phrase in lower_ans
            for phrase in (
                "insufficient evidence",
                "does not contain enough information",
                "do not contain sufficient",
                "not mentioned in the provided",
                "not available in the retrieved",
            )
        )

        return KnowledgeAskResponse(
            question=question,
            answer=answer_text.strip(),
            sources=sources,
            insufficient_evidence=insufficient,
            retrieval_note=f"Grounded in {len(sources)} retrieved passage(s) (similarity >= {settings.RAG_RELEVANCE_THRESHOLD:.2f}).",
            model_used=settings.GEMINI_MODEL,
        )


rag_service = RAGService()
