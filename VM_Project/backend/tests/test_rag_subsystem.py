"""Comprehensive unit and integration tests for the InsureDesk AI RAG subsystem.

Designed to run with both `pytest` and `python3 -m unittest`.
Mocks external C-extension/API dependencies (`fitz`, `chromadb`, `google.genai`,
and `sqlalchemy` when unavailable in offline test environments) while testing
all RAG validation, chunking, embedding retry, vector filtering, grounded Q&A,
and Investigator/Watchdog registry isolation logic.
"""

import hashlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _ensure_stub_modules():
    """Use real installed packages whenever available; provide Pydantic-v2-compatible stubs only if missing."""
    try:
        import pydantic_settings  # noqa: F401
    except ImportError:
        import pydantic as _pydantic

        ps = types.ModuleType("pydantic_settings")

        class _CompatBaseSettings(_pydantic.BaseModel):
            model_config = {"extra": "ignore"}

        class _SettingsConfigDict(dict):
            pass

        ps.BaseSettings = _CompatBaseSettings
        ps.SettingsConfigDict = _SettingsConfigDict
        sys.modules["pydantic_settings"] = ps

    import pydantic as _pydantic
    if not hasattr(_pydantic, "field_validator"):
        def _field_validator(*args, **kwargs):
            def _dec(fn):
                return fn
            return _dec
        _pydantic.field_validator = _field_validator

    try:
        from google import genai  # noqa: F401
    except ImportError:
        if "google" not in sys.modules:
            sys.modules["google"] = types.ModuleType("google")
        genai_mod = types.ModuleType("google.genai")
        types_mod = types.ModuleType("google.genai.types")

        class _DummyConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

        types_mod.GenerateContentConfig = _DummyConfig
        types_mod.HttpOptions = _DummyConfig
        types_mod.EmbedContentConfig = _DummyConfig
        types_mod.AutomaticFunctionCallingConfig = _DummyConfig
        types_mod.Content = _DummyConfig
        types_mod.Part = MagicMock()
        genai_mod.Client = MagicMock()
        genai_mod.types = types_mod
        sys.modules["google.genai"] = genai_mod
        sys.modules["google.genai.types"] = types_mod
        sys.modules["google"].genai = genai_mod

    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        sa = types.ModuleType("sqlalchemy")
        sa.Boolean = sa.Date = sa.DateTime = sa.ForeignKey = sa.Index = MagicMock()
        sa.Integer = sa.String = sa.Text = sa.Float = sa.JSON = MagicMock()
        sa.create_engine = MagicMock()
        sa.event = MagicMock()
        sa.func = MagicMock()
        sa.select = MagicMock()
        sa.text = MagicMock()
        sa.or_ = sa.and_ = sa.desc = sa.asc = MagicMock()
        sys.modules["sqlalchemy"] = sa

        sa_ext = types.ModuleType("sqlalchemy.ext")
        sa_async = types.ModuleType("sqlalchemy.ext.asyncio")
        sa_async.AsyncSession = MagicMock()
        sa_async.async_sessionmaker = MagicMock()
        sa_async.create_async_engine = MagicMock()
        sys.modules["sqlalchemy.ext"] = sa_ext
        sys.modules["sqlalchemy.ext.asyncio"] = sa_async

        sa_orm = types.ModuleType("sqlalchemy.orm")
        sa_orm.Session = MagicMock()
        sa_orm.sessionmaker = MagicMock()
        sa_orm.Mapped = MagicMock()
        sa_orm.mapped_column = MagicMock(return_value=None)
        sa_orm.relationship = MagicMock()
        sa_orm.selectinload = MagicMock()
        sa_orm.DeclarativeBase = object
        sys.modules["sqlalchemy.orm"] = sa_orm


_ensure_stub_modules()

from app.rag.document_loader import (  # noqa: E402
    DocumentExtractionError,
    DocumentValidationError,
    extract_pdf_pages,
    sanitize_filename,
    save_pdf_securely,
    validate_pdf_upload,
)
from app.rag.embedding_service import EmbeddingError, GeminiEmbeddingService  # noqa: E402
from app.rag.retriever import KnowledgeRetriever  # noqa: E402
from app.rag.schemas import DocumentChunk, ExtractedPage  # noqa: E402
from app.rag.text_chunker import TextChunker  # noqa: E402
from app.rag.vector_store import ChromaVectorStore  # noqa: E402


class TestDocumentLoaderAndValidation(unittest.TestCase):
    """Tests for PDF upload validation, security, and PyMuPDF extraction."""

    def test_valid_pdf_upload_validation(self):
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        name, file_hash = validate_pdf_upload(
            filename="../unsafe/../../Motor_Policy_2026.pdf",
            content_type="application/pdf",
            file_bytes=pdf_bytes,
        )
        self.assertEqual(name, "Motor_Policy_2026.pdf")
        self.assertEqual(file_hash, hashlib.sha256(pdf_bytes).hexdigest())

    def test_invalid_extension_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_pdf_upload("malware.exe", "application/octet-stream", b"%PDF-1.4")

    def test_invalid_mime_type_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_pdf_upload("fake.pdf", "text/plain", b"%PDF-1.4")

    def test_invalid_magic_header_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_pdf_upload("not_a_pdf.pdf", "application/pdf", b"<html>not pdf</html>")

    def test_empty_file_rejected(self):
        with self.assertRaises(DocumentValidationError):
            validate_pdf_upload("empty.pdf", "application/pdf", b"")

    def test_oversized_file_rejected(self):
        big_bytes = b"%PDF-1.4" + (b"0" * (2 * 1024 * 1024))
        with self.assertRaises(DocumentValidationError):
            validate_pdf_upload("big.pdf", "application/pdf", big_bytes, max_size_mb=1)

    def test_sanitize_filename_prevents_traversal(self):
        self.assertEqual(sanitize_filename("../../etc/passwd.pdf"), "passwd.pdf")
        self.assertTrue(sanitize_filename("policy doc").endswith(".pdf"))

    def test_save_pdf_securely(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            doc_id, path = save_pdf_securely(b"%PDF-1.4 test", upload_dir=tmpdir)
            self.assertTrue(os.path.exists(path))
            self.assertEqual(Path(path).name, f"{doc_id}.pdf")

    def test_extract_pdf_pages_preserves_page_numbers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 dummy")

            page1 = MagicMock()
            page1.get_text.return_value = "Section 1: Accidental Damage Coverage applies to collisions."
            page2 = MagicMock()
            page2.get_text.return_value = "Section 2: Exclusions include racing and DUI."

            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 2
            mock_doc.__getitem__.side_effect = [page1, page2]

            mock_fitz = MagicMock()
            mock_fitz.open.return_value = mock_doc

            with patch("app.rag.document_loader.fitz", mock_fitz):
                total_pages, pages = extract_pdf_pages(str(pdf_path))

            self.assertEqual(total_pages, 2)
            self.assertEqual(len(pages), 2)
            self.assertEqual(pages[0].page_number, 1)
            self.assertEqual(pages[1].page_number, 2)
            self.assertIn("Accidental Damage", pages[0].text)

    def test_scanned_pdf_raises_extraction_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "scanned.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 scanned")

            blank_page = MagicMock()
            blank_page.get_text.return_value = "   \n  "
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.side_effect = [blank_page]

            mock_fitz = MagicMock()
            mock_fitz.open.return_value = mock_doc

            with patch("app.rag.document_loader.fitz", mock_fitz):
                with self.assertRaises(DocumentExtractionError) as ctx:
                    extract_pdf_pages(str(pdf_path))
                self.assertIn("scanned", str(ctx.exception).lower())

    def test_corrupted_pdf_raises_extraction_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "corrupt.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 corrupt")

            mock_fitz = MagicMock()
            mock_fitz.open.side_effect = RuntimeError("cannot open broken file")

            with patch("app.rag.document_loader.fitz", mock_fitz):
                with self.assertRaises(DocumentExtractionError):
                    extract_pdf_pages(str(pdf_path))


class TestTextChunker(unittest.TestCase):
    """Tests for configurable chunking, page preservation, and deduplication."""

    def test_chunk_pages_preserves_metadata_and_deduplicates(self):
        chunker = TextChunker(chunk_size=220, chunk_overlap=40)
        pages = [
            ExtractedPage(
                page_number=1,
                text=(
                    "Accidental damage is covered under Comprehensive Motor Insurance up to the Insured Declared Value. "
                    "A standard deductible of $250 applies per claim. "
                    "Flood and storm damage are also included under natural calamities coverage."
                ),
            ),
            ExtractedPage(
                page_number=2,
                text="   ",  # Should be ignored
            ),
            ExtractedPage(
                page_number=3,
                text="General Exclusion: Driving without a valid license voids accidental damage claims.",
            ),
        ]
        chunks = chunker.chunk_pages(
            pages=pages,
            document_id="doc-123",
            document_name="Motor_Policy.pdf",
            category="Insurance Policy Documents",
            policy_type="AUTO",
        )
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(c.text.strip() for c in chunks))
        self.assertEqual(chunks[0].document_id, "doc-123")
        self.assertEqual(chunks[0].page_number, 1)
        self.assertEqual(chunks[-1].page_number, 3)
        self.assertEqual(chunks[-1].policy_type, "AUTO")


class TestEmbeddingService(unittest.TestCase):
    """Tests for Gemini embedding generation, retry on rate limits, and failure handling."""

    def test_embed_documents_retries_on_429_and_succeeds(self):
        svc = GeminiEmbeddingService(model_name="gemini-embedding-001", batch_size=2, max_retries=3, base_backoff_seconds=0.01)

        emb1 = MagicMock()
        emb1.values = [0.1, 0.2, 0.3]
        emb2 = MagicMock()
        emb2.values = [0.4, 0.5, 0.6]
        ok_resp = MagicMock()
        ok_resp.embeddings = [emb1, emb2]

        mock_client = MagicMock()
        mock_client.models.embed_content.side_effect = [
            RuntimeError("429 Resource Exhausted rate limit"),
            ok_resp,
        ]

        with patch("app.rag.embedding_service.gemini_client") as mock_gc:
            mock_gc.is_live.return_value = True
            mock_gc.client = mock_client
            vectors = svc.embed_documents(["chunk 1", "chunk 2"])

        self.assertEqual(len(vectors), 2)
        self.assertEqual(vectors[0], [0.1, 0.2, 0.3])
        self.assertEqual(mock_client.models.embed_content.call_count, 2)

    def test_embed_documents_raises_when_offline(self):
        svc = GeminiEmbeddingService()
        with patch("app.rag.embedding_service.gemini_client") as mock_gc:
            mock_gc.is_live.return_value = False
            mock_gc.client = None
            with self.assertRaises(EmbeddingError):
                svc.embed_documents(["hello"])


class TestVectorStoreAndRetriever(unittest.TestCase):
    """Tests for ChromaVectorStore operations and KnowledgeRetriever threshold filtering."""

    def test_vector_store_upsert_search_filter_and_delete(self):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            "ids": [["doc1_p1_c0", "doc2_p2_c0"]],
            "documents": [["Accidental damage is covered.", "Unrelated life policy note."]],
            "metadatas": [[
                {"document_id": "doc1", "document_name": "Motor.pdf", "category": "Insurance Policy Documents", "page_number": 1},
                {"document_id": "doc2", "document_name": "Life.pdf", "category": "Insurance Policy Documents", "page_number": 2},
            ]],
            "distances": [[0.12, 0.78]],  # similarities: 0.88 and 0.22
        }

        store = ChromaVectorStore(persist_directory="./tmp_chroma")
        store._get_collection = MagicMock(return_value=mock_collection)

        chunks = [
            DocumentChunk(
                chunk_id="doc1_p1_c0",
                document_id="doc1",
                document_name="Motor.pdf",
                category="Insurance Policy Documents",
                policy_type="AUTO",
                page_number=1,
                chunk_index=0,
                text="Accidental damage is covered.",
                char_count=29,
            )
        ]
        upserted = store.upsert_chunks(chunks, [[0.1, 0.9]])
        self.assertEqual(upserted, 1)
        mock_collection.upsert.assert_called_once()

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1, 0.9]
        retriever = KnowledgeRetriever(embedder=mock_embedder, store=store, relevance_threshold=0.50)

        passages = retriever.retrieve("Is accidental damage covered?", category="Insurance Policy Documents")
        # Only doc1_p1_c0 (similarity 0.88 >= 0.50) should be returned; unrelated 0.22 filtered out
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0].document_name, "Motor.pdf")
        self.assertEqual(passages[0].page_number, 1)

        store.delete_document_chunks("doc1")
        mock_collection.delete.assert_called_once_with(where={"document_id": "doc1"})


class TestRAGServiceAndInvestigatorIntegration(unittest.TestCase):
    """Tests for grounded Q&A, insufficient/conflicting evidence, and Investigator vs Watchdog isolation."""

    def test_ask_question_insufficient_evidence(self):
        from app.rag.rag_service import RAGService

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        service = RAGService(retriever=mock_retriever)

        resp = service.ask_question("What is the Mars colonization exclusion?")
        self.assertTrue(resp.insufficient_evidence)
        self.assertEqual(resp.sources, [])
        self.assertIn("Insufficient evidence", resp.answer)

    def test_ask_question_grounded_answer_with_citations(self):
        from app.rag.rag_service import RAGService
        from app.rag.schemas import RetrievedPassage

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            RetrievedPassage(
                chunk_id="d1_p4_c0",
                document_id="d1",
                document_name="Motor_Policy_Wording.pdf",
                category="Insurance Policy Documents",
                policy_type="AUTO",
                page_number=4,
                relevant_excerpt="Accidental damage to the insured vehicle is covered subject to a $250 deductible.",
                similarity_score=0.91,
            )
        ]
        service = RAGService(retriever=mock_retriever)

        with patch("app.rag.rag_service.gemini_client") as mock_gc:
            mock_gc.is_live.return_value = True
            mock_gc.generate_structured_analysis.return_value = (
                "Accidental damage to the insured vehicle is covered with a $250 deductible "
                "[Motor_Policy_Wording.pdf, Page 4]."
            )
            resp = service.ask_question("Is accidental damage covered?")

        self.assertFalse(resp.insufficient_evidence)
        self.assertEqual(len(resp.sources), 1)
        self.assertEqual(resp.sources[0].page_number, 4)
        self.assertIn("Motor_Policy_Wording.pdf", resp.answer)

    def test_ask_question_gemini_failure_preserves_sources(self):
        from app.rag.rag_service import RAGService
        from app.rag.schemas import RetrievedPassage

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            RetrievedPassage(
                chunk_id="d1_p2_c0",
                document_id="d1",
                document_name="Claims_Guide.pdf",
                category="Claim Guidelines",
                page_number=2,
                relevant_excerpt="Claims must be reported within 48 hours of the incident.",
                similarity_score=0.85,
            )
        ]
        service = RAGService(retriever=mock_retriever)

        with patch("app.rag.rag_service.gemini_client") as mock_gc:
            mock_gc.is_live.return_value = True
            mock_gc.generate_structured_analysis.return_value = None  # Simulates timeout/error
            resp = service.ask_question("What is the claim reporting window?")

        self.assertEqual(len(resp.sources), 1)
        self.assertIn("timed out or returned an error", resp.answer)

    def test_tool_registry_investigator_has_rag_but_watchdog_isolated(self):
        # Verify rag_tools and tool_registry isolation without mutating Watchdog
        from app.agent.tools.rag_tools import search_insurance_documents

        with patch("app.rag.rag_service.rag_service") as mock_rag:
            mock_rag.search_documents.return_value = MagicMock(total_results=0, passages=[])
            res = search_insurance_documents("accidental damage")
            self.assertEqual(res["total_results"], 0)
            self.assertIn("No relevant passages", res["message"])

        # Check tool_registry.py source directly to ensure Watchdog list does NOT include search_insurance_documents
        registry_src = (BACKEND_DIR / "app" / "agent" / "tool_registry.py").read_text(encoding="utf-8")
        watchdog_block = registry_src.split("self._watchdog_tool_names")[1].split("]")[0]
        self.assertNotIn("search_insurance_documents", watchdog_block)
        self.assertIn('self.register("search_insurance_documents", search_insurance_documents)', registry_src)




class TestCorrectionsReliabilityAndPolicyFiltering(unittest.TestCase):
    """Tests for Phase 2-5 corrections: policy_type filtering, bounded upload, safe delete & reindex."""

    def test_policy_type_filtering_passed_to_vector_store(self):
        mock_collection = MagicMock()
        mock_collection.count.return_value = 2
        mock_collection.query.return_value = {
            "ids": [["auto_p1_c0"]],
            "documents": [["Collision damage is covered under Motor Comprehensive Policy."]],
            "metadatas": [[
                {
                    "document_id": "auto-1",
                    "document_name": "Motor_Policy.pdf",
                    "category": "Insurance Policy Documents",
                    "policy_type": "AUTO",
                    "page_number": 1,
                }
            ]],
            "distances": [[0.10]],
        }
        store = ChromaVectorStore(persist_directory="./tmp_chroma")
        store._get_collection = MagicMock(return_value=mock_collection)

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.2, 0.8]
        retriever = KnowledgeRetriever(embedder=mock_embedder, store=store, relevance_threshold=0.45)

        passages = retriever.retrieve("accidental damage", policy_type="auto")
        self.assertEqual(len(passages), 1)
        self.assertEqual(passages[0].policy_type, "AUTO")
        call_kwargs = mock_collection.query.call_args.kwargs
        self.assertEqual(call_kwargs["where"], {"policy_type": "AUTO"})

    def test_bounded_upload_rejects_oversized_stream_early(self):
        import asyncio
        from app.api.v1.endpoints.knowledge_base import _read_upload_bounded

        class _FakeUploadFile:
            def __init__(self, chunks):
                self._chunks = list(chunks)
                self.reads = 0

            async def read(self, size=-1):
                self.reads += 1
                return self._chunks.pop(0) if self._chunks else b""

        fake_file = _FakeUploadFile([b"A" * 600, b"B" * 600, b"C" * 600])
        with self.assertRaises(DocumentValidationError):
            asyncio.run(_read_upload_bounded(fake_file, max_bytes=1000, chunk_size=600))
        # Stopped reading on chunk 2 instead of draining chunk 3
        self.assertEqual(fake_file.reads, 2)

    def test_delete_document_preserves_metadata_when_file_removal_fails(self):
        from app.rag.rag_service import RAGService

        mock_doc = MagicMock()
        mock_doc.id = "doc-del-1"
        mock_doc.document_name = "Motor_Policy.pdf"
        mock_doc.file_location = "/tmp/nonexistent_but_mocked.pdf"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = mock_doc

        mock_store = MagicMock()
        service = RAGService(store=mock_store)

        with patch("app.rag.rag_service.os.path.exists", return_value=True), \
             patch("app.rag.rag_service.Path.unlink", side_effect=OSError("Permission denied")):
            with self.assertRaises(RuntimeError) as ctx:
                service.delete_document("doc-del-1", db=mock_session)

        self.assertIn("Metadata preserved", str(ctx.exception))
        mock_store.delete_document_chunks.assert_called_once_with("doc-del-1")
        mock_session.delete.assert_not_called()

    def test_reindex_preserves_existing_vectors_when_embedding_fails(self):
        from app.rag.rag_service import RAGService

        mock_doc = MagicMock()
        mock_doc.id = "doc-reidx-1"
        mock_doc.document_name = "Health_Policy.pdf"
        mock_doc.category = "Insurance Policy Documents"
        mock_doc.policy_type = "HEALTH"
        mock_doc.file_location = "/tmp/health.pdf"
        mock_doc.processing_status = "COMPLETED"

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.first.return_value = mock_doc

        mock_store = MagicMock()
        mock_embedder = MagicMock()
        mock_embedder.embed_documents.side_effect = EmbeddingError("Gemini 429 rate limit")

        service = RAGService(embedder=mock_embedder, store=mock_store)
        mock_doc.file_hash = "abc123"
        mock_doc.file_size_bytes = 1024
        mock_doc.page_count = 1
        mock_doc.chunk_count = 1
        mock_doc.error_message = None
        mock_doc.upload_timestamp = "2026-11-23T00:00:00Z"
        mock_doc.last_indexed_timestamp = None

        from app.rag.schemas import KnowledgeDocumentResponse
        compat_cm = (
            patch.object(KnowledgeDocumentResponse, "model_validate", side_effect=lambda obj: KnowledgeDocumentResponse(id=obj.id, document_name=obj.document_name, category=obj.category, policy_type=obj.policy_type, file_hash=obj.file_hash, file_size_bytes=obj.file_size_bytes, processing_status=obj.processing_status, page_count=obj.page_count, chunk_count=obj.chunk_count, error_message=obj.error_message, upload_timestamp=obj.upload_timestamp, last_indexed_timestamp=obj.last_indexed_timestamp), create=True)
            if not hasattr(KnowledgeDocumentResponse, "model_validate")
            else patch("app.rag.rag_service.logger")
        )
        with compat_cm, patch("app.rag.rag_service.extract_pdf_pages", return_value=(1, [ExtractedPage(page_number=1, text="Health policy coverage terms.")])):
            res = service.reindex_document("doc-reidx-1", db=mock_session)

        self.assertEqual(res.processing_status, "FAILED")
        # Existing ChromaDB vectors must NOT be deleted when embedding fails!
        mock_store.delete_document_chunks.assert_not_called()
        mock_store.delete_chunk_ids.assert_not_called()
        mock_store.upsert_chunks.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
