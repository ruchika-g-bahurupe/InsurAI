"""Configurable, page-preserving text chunker for insurance documents."""

import hashlib
import re
from typing import List, Optional, Set
from app.core.config import settings
from app.rag.schemas import DocumentChunk, ExtractedPage


class TextChunker:
    """Splits extracted PDF pages into overlapping semantic chunks."""

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = max(200, chunk_size if chunk_size is not None else settings.RAG_CHUNK_SIZE)
        self.chunk_overlap = max(
            0,
            min(
                chunk_overlap if chunk_overlap is not None else settings.RAG_CHUNK_OVERLAP,
                self.chunk_size // 2,
            ),
        )

    def chunk_pages(
        self,
        pages: List[ExtractedPage],
        document_id: str,
        document_name: str,
        category: str,
        policy_type: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """Chunk extracted pages while preserving page numbers and metadata."""
        chunks: List[DocumentChunk] = []
        seen_hashes: Set[str] = set()
        global_chunk_index = 0

        for page in pages:
            page_chunks = self._split_text(page.text)
            for local_idx, raw_chunk in enumerate(page_chunks):
                cleaned = raw_chunk.strip()
                if not cleaned:
                    continue

                # Avoid duplicate chunks across identical headers/footers or repeated blocks
                norm_hash = hashlib.sha256(
                    re.sub(r"\s+", " ", cleaned.lower()).encode("utf-8")
                ).hexdigest()
                if norm_hash in seen_hashes:
                    continue
                seen_hashes.add(norm_hash)

                chunk_id = f"{document_id}_p{page.page_number}_c{local_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        document_name=document_name,
                        category=category,
                        policy_type=policy_type,
                        page_number=page.page_number,
                        chunk_index=global_chunk_index,
                        text=cleaned,
                        char_count=len(cleaned),
                    )
                )
                global_chunk_index += 1

        return chunks

    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks of <= chunk_size with overlap, preferring paragraph/sentence boundaries."""
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        results: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            if end < text_len:
                # Prefer breaking at paragraph, then sentence, then whitespace
                window = text[start:end]
                break_pos = self._find_break_position(window)
                if break_pos > self.chunk_size // 3:
                    end = start + break_pos

            chunk = text[start:end].strip()
            if chunk:
                results.append(chunk)

            if end >= text_len:
                break

            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = end
            start = next_start

        return results

    @staticmethod
    def _find_break_position(window: str) -> int:
        """Find the cleanest split boundary inside a window."""
        para_idx = window.rfind("\n\n")
        if para_idx != -1:
            return para_idx

        for punct in (". ", ".\n", "? ", "! ", "; "):
            idx = window.rfind(punct)
            if idx != -1:
                return idx + 1

        newline_idx = window.rfind("\n")
        if newline_idx != -1:
            return newline_idx

        space_idx = window.rfind(" ")
        if space_idx != -1:
            return space_idx

        return len(window)
