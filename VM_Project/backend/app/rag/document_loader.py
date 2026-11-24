"""PDF Document Loader & Validator using PyMuPDF (fitz)."""

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import List, Tuple

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - handled gracefully when PyMuPDF is missing
    fitz = None  # type: ignore

from app.core.config import settings
from app.core.logging import logger
from app.rag.schemas import ExtractedPage


ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/x-pdf"}
PDF_MAGIC_HEADER = b"%PDF-"


class DocumentValidationError(ValueError):
    """Raised when an uploaded file fails PDF validation or security checks."""


class DocumentExtractionError(RuntimeError):
    """Raised when PDF text extraction fails or yields no extractable text."""


def sanitize_filename(filename: str) -> str:
    """Strip directory components and unsafe characters to prevent path traversal."""
    base = os.path.basename(filename or "document.pdf")
    cleaned = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base).strip()
    if not cleaned or cleaned in {".", ".."}:
        cleaned = "document.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned[:180]


def validate_pdf_upload(
    filename: str,
    content_type: str | None,
    file_bytes: bytes,
    max_size_mb: int | None = None,
) -> Tuple[str, str]:
    """
    Validate extension, MIME type, size limit, and PDF magic header.
    Returns (sanitized_filename, sha256_hash).
    """
    if not filename:
        raise DocumentValidationError("Filename is required.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError(
            f"Unsupported file extension '{ext or 'none'}'. Only PDF (.pdf) files are accepted."
        )

    if content_type and content_type.lower().split(";")[0].strip() not in ALLOWED_MIME_TYPES:
        raise DocumentValidationError(
            f"Unsupported MIME type '{content_type}'. Expected application/pdf."
        )

    if not file_bytes or len(file_bytes) == 0:
        raise DocumentValidationError("Uploaded PDF file is empty (0 bytes).")

    limit_mb = max_size_mb or settings.RAG_MAX_FILE_SIZE_MB
    max_bytes = limit_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise DocumentValidationError(
            f"File size ({len(file_bytes) / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {limit_mb} MB."
        )

    if not file_bytes.lstrip().startswith(PDF_MAGIC_HEADER):
        raise DocumentValidationError(
            "Invalid PDF file content: file does not start with a valid %PDF- header."
        )

    safe_name = sanitize_filename(filename)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    return safe_name, file_hash


def save_pdf_securely(file_bytes: bytes, upload_dir: str | None = None) -> Tuple[str, str]:
    """
    Persist PDF bytes to a generated UUID filename inside the configured upload directory.
    Prevents path traversal and sets restrictive file permissions (0o600 where supported).
    Returns (document_id, relative_or_resolved_storage_path).
    """
    target_dir = Path(upload_dir or settings.RAG_UPLOAD_DIR).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    doc_id = str(uuid.uuid4())
    target_path = (target_dir / f"{doc_id}.pdf").resolve()
    if target_path.parent != target_dir:
        raise DocumentValidationError("Invalid storage path detected.")

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    try:
        os.chmod(target_path, 0o600)
    except OSError:
        pass  # Windows or restricted FS may ignore POSIX chmod

    return doc_id, str(target_path)


def extract_pdf_pages(file_path: str) -> Tuple[int, List[ExtractedPage]]:
    """
    Extract text page-by-page from a PDF using PyMuPDF (fitz).
    Returns (total_page_count, list_of_ExtractedPage).
    Raises DocumentExtractionError for unreadable, empty, or scanned-only PDFs.
    """
    if fitz is None:
        raise DocumentExtractionError(
            "PyMuPDF (fitz) is not installed in the Python environment. Install PyMuPDF to extract PDF text."
        )

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise DocumentExtractionError("Stored PDF file could not be located on disk.")

    try:
        doc = fitz.open(str(path))
    except Exception as e:
        logger.error(f"PyMuPDF failed to open PDF '{path.name}': {e}")
        raise DocumentExtractionError(f"Unable to read PDF file (corrupted or encrypted): {e}")

    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise DocumentExtractionError("PDF contains 0 pages.")

        extracted_pages: List[ExtractedPage] = []
        for idx in range(total_pages):
            page = doc[idx]
            raw_text = page.get_text("text") or ""
            cleaned = _normalize_page_text(raw_text)
            if cleaned:
                extracted_pages.append(
                    ExtractedPage(page_number=idx + 1, text=cleaned)
                )

        if not extracted_pages:
            raise DocumentExtractionError(
                "No extractable text was found in this PDF. It appears to be a scanned image-only PDF, "
                "and OCR is not configured in this environment."
            )

        return total_pages, extracted_pages
    finally:
        doc.close()


def _normalize_page_text(text: str) -> str:
    """Normalize whitespace while preserving paragraph breaks."""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()
