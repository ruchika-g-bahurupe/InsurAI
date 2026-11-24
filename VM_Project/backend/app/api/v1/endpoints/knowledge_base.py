"""Insurance Knowledge Base & RAG API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings
from app.rag.document_loader import DocumentValidationError
from app.rag.embedding_service import EmbeddingError
from app.rag.rag_service import rag_service
from app.rag.schemas import (
    DocumentCategory,
    DocumentUploadResponse,
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    KnowledgeBaseStatsResponse,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.rag.vector_store import VectorStoreError

router = APIRouter(prefix="/knowledge-base", tags=["Insurance Knowledge Base (RAG)"])


@router.get("/stats", response_model=KnowledgeBaseStatsResponse)
async def get_knowledge_base_stats():
    """Return real-time Knowledge Base document and chunk counts."""
    return await run_in_threadpool(rag_service.get_stats)


@router.get("/categories", response_model=List[str])
async def list_document_categories():
    """List supported Insurance Knowledge Base document categories."""
    return [c.value for c in DocumentCategory]


async def _read_upload_bounded(file: UploadFile, max_bytes: int, chunk_size: int = 1024 * 1024) -> bytes:
    """Read an uploaded file in chunks and abort early if it exceeds max_bytes."""
    chunks = bytearray()
    total_read = 0
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_read += len(chunk)
        if total_read > max_bytes:
            raise DocumentValidationError(
                f"File size exceeds maximum allowed limit of {settings.RAG_MAX_FILE_SIZE_MB} MB."
            )
        chunks.extend(chunk)
    return bytes(chunks)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    policy_type: Optional[str] = Form(None),
):
    """Upload, validate, deduplicate, and index an insurance PDF document."""
    max_bytes = settings.RAG_MAX_FILE_SIZE_MB * 1024 * 1024
    try:
        file_bytes = await _read_upload_bounded(file, max_bytes=max_bytes)
        return await run_in_threadpool(
            rag_service.upload_document,
            filename=file.filename or "document.pdf",
            content_type=file.content_type,
            file_bytes=file_bytes,
            category=category,
            policy_type=policy_type,
        )
    except DocumentValidationError as dve:
        raise HTTPException(status_code=400, detail=str(dve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload knowledge document: {str(e)}")
    finally:
        await file.close()


@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    category: Optional[str] = Query(None, description="Filter by document category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
):
    """List all uploaded Insurance Knowledge Base documents."""
    return await run_in_threadpool(
        rag_service.list_documents,
        category=category,
        status=status,
    )


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentDetailResponse)
async def get_knowledge_document(document_id: str):
    """Retrieve metadata, processing status, and indexed excerpts for a document."""
    try:
        return await run_in_threadpool(rag_service.get_document_status, document_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/documents/{document_id}/file")
async def view_knowledge_document_file(document_id: str):
    """Serve the stored PDF inline for viewing in the browser."""
    try:
        info = await run_in_threadpool(rag_service.get_document_file_info, document_id)
        return FileResponse(
            path=info["file_path"],
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{info["document_name"]}"'},
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except FileNotFoundError as fnfe:
        raise HTTPException(status_code=404, detail=str(fnfe))


@router.post("/documents/{document_id}/reindex", response_model=KnowledgeDocumentResponse)
async def reindex_knowledge_document(document_id: str):
    """Re-extract, re-chunk, re-embed, and re-index an existing knowledge document."""
    try:
        return await run_in_threadpool(rag_service.reindex_document, document_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_knowledge_document(document_id: str):
    """Safely delete a knowledge document and all associated ChromaDB vector chunks."""
    try:
        return await run_in_threadpool(rag_service.delete_document, document_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except VectorStoreError as vse:
        raise HTTPException(status_code=500, detail=str(vse))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_base(payload: KnowledgeSearchRequest):
    """Semantic search over indexed insurance knowledge base passages."""
    try:
        return await run_in_threadpool(
            rag_service.search_documents,
            query=payload.query,
            category=payload.category,
            policy_type=payload.policy_type,
            document_id=payload.document_id,
            top_k=payload.top_k,
        )
    except EmbeddingError as ee:
        raise HTTPException(status_code=503, detail=str(ee))
    except VectorStoreError as vse:
        raise HTTPException(status_code=503, detail=str(vse))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {str(e)}")


@router.post("/ask", response_model=KnowledgeAskResponse)
async def ask_knowledge_base(payload: KnowledgeAskRequest):
    """Ask a natural-language question answered strictly from retrieved insurance documents."""
    try:
        return await run_in_threadpool(
            rag_service.ask_question,
            question=payload.question,
            category=payload.category,
            policy_type=payload.policy_type,
            document_id=payload.document_id,
            top_k=payload.top_k,
        )
    except EmbeddingError as ee:
        raise HTTPException(status_code=503, detail=str(ee))
    except VectorStoreError as vse:
        raise HTTPException(status_code=503, detail=str(vse))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge Q&A failed: {str(e)}")
