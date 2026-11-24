"""Pydantic v2 schemas for the Insurance Knowledge Base & RAG subsystem."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    """Supported initial insurance knowledge document categories."""
    INSURANCE_POLICY_DOCUMENTS = "Insurance Policy Documents"
    CLAIM_GUIDELINES = "Claim Guidelines"
    INSURANCE_TERMS_AND_CONDITIONS = "Insurance Terms and Conditions"
    UNDERWRITING_GUIDELINES = "Underwriting Guidelines"
    INSURANCE_OPERATIONAL_PROCEDURES = "Insurance Operational Procedures"


class ProcessingStatus(str, Enum):
    """Document ingestion and indexing lifecycle stages."""
    UPLOADED = "UPLOADED"
    EXTRACTING_TEXT = "EXTRACTING_TEXT"
    CHUNKING = "CHUNKING"
    GENERATING_EMBEDDINGS = "GENERATING_EMBEDDINGS"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExtractedPage(BaseModel):
    """Text extracted from a single PDF page."""
    page_number: int = Field(..., ge=1)
    text: str


class DocumentChunk(BaseModel):
    """A single chunk ready for embedding and vector indexing."""
    chunk_id: str
    document_id: str
    document_name: str
    category: str
    policy_type: Optional[str] = None
    page_number: int = Field(..., ge=1)
    chunk_index: int = Field(..., ge=0)
    text: str
    char_count: int


class KnowledgeDocumentResponse(BaseModel):
    """API response schema for a Knowledge Base document."""
    id: str
    document_name: str
    category: str
    policy_type: Optional[str] = None
    file_hash: str
    file_size_bytes: int
    processing_status: str
    page_count: int
    chunk_count: int
    error_message: Optional[str] = None
    upload_timestamp: datetime
    last_indexed_timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KnowledgeDocumentDetailResponse(KnowledgeDocumentResponse):
    """Detailed document view including sample extracted/indexed excerpts."""
    excerpts: List[Dict[str, Any]] = Field(default_factory=list)


class KnowledgeBaseStatsResponse(BaseModel):
    """Real-time Knowledge Base dashboard statistics."""
    total_documents: int
    indexed_documents: int
    processing_documents: int
    failed_documents: int
    total_chunks: int
    categories_breakdown: Dict[str, int] = Field(default_factory=dict)


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading and processing a PDF."""
    document: KnowledgeDocumentResponse
    is_duplicate: bool = False
    message: str


class KnowledgeSearchRequest(BaseModel):
    """Semantic search request against the insurance knowledge base."""
    query: str = Field(..., min_length=2, max_length=1000)
    category: Optional[str] = None
    policy_type: Optional[str] = None
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedPassage(BaseModel):
    """A single retrieved passage with source metadata and similarity score."""
    chunk_id: str
    document_id: str
    document_name: str
    category: str
    policy_type: Optional[str] = None
    page_number: int
    relevant_excerpt: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)


class KnowledgeSearchResponse(BaseModel):
    """Response for semantic passage search."""
    query: str
    total_results: int
    passages: List[RetrievedPassage]


class KnowledgeAskRequest(BaseModel):
    """Question-answering request against the insurance knowledge base."""
    question: str = Field(..., min_length=2, max_length=2000)
    category: Optional[str] = None
    policy_type: Optional[str] = None
    document_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=15)


class SourceCitation(BaseModel):
    """Traceable source reference for a grounded RAG answer."""
    document_id: str
    document_name: str
    category: str
    page_number: int
    relevant_excerpt: str
    retrieval_similarity: float


class KnowledgeAskResponse(BaseModel):
    """Grounded RAG Q&A response with source attribution and evidence indicator."""
    question: str
    answer: str
    sources: List[SourceCitation]
    insufficient_evidence: bool = False
    retrieval_note: Optional[str] = None
    model_used: Optional[str] = None
