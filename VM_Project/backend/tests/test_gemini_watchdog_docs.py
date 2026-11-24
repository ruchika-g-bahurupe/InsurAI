"""Tests for Gemini integration, Autonomous Watchdog manual tool-dispatch, and Documentation viewing."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.test_rag_subsystem import _ensure_stub_modules  # noqa: E402

_ensure_stub_modules()

from app.agent.gemini_client import GeminiClientWrapper  # noqa: E402
from app.agent.intelligence_core import IntelligenceCore  # noqa: E402
from app.rag.rag_service import RAGService  # noqa: E402


class TestGeminiClientIntegration(unittest.TestCase):
    """Tests for API key handling, AFC disablement, connectivity check, and error sanitization."""

    def test_generate_with_tools_disables_automatic_function_calling(self):
        mock_sdk_client = MagicMock()
        mock_resp = MagicMock()
        mock_sdk_client.models.generate_content.return_value = mock_resp

        wrapper = GeminiClientWrapper()
        wrapper.api_key = "AIzaSyDummyTestKey1234567890"
        wrapper.model = "gemini-3.8-flash"
        wrapper.analysis_model = "gemini-3.8-flash"
        wrapper._client = mock_sdk_client

        res = wrapper.generate_with_tools(
            system_instruction="Watchdog prompt",
            contents=["hello"],
            tools=[lambda: None],
            use_analysis_model=True,
        )
        self.assertIs(res, mock_resp)
        call_kwargs = mock_sdk_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-3.8-flash")
        afc_cfg = call_kwargs["config"].automatic_function_calling
        self.assertTrue(afc_cfg.disable)

    def test_connectivity_check_and_error_redaction(self):
        secret = "AIzaSySecretKey999999999"
        mock_sdk_client = MagicMock()
        mock_sdk_client.models.generate_content.side_effect = RuntimeError(
            f"404 NOT_FOUND for key {secret}: model gemini-2.5-flash not found"
        )

        wrapper = GeminiClientWrapper()
        wrapper.api_key = secret
        wrapper.model = "gemini-2.5-flash"
        wrapper._client = mock_sdk_client

        result = wrapper.test_connectivity()
        self.assertFalse(result["connected"])
        self.assertIn("404 NOT_FOUND", result["error"])
        self.assertNotIn(secret, result["error"])
        self.assertIn("[REDACTED]", result["error"])


class TestWatchdogManualToolDispatch(unittest.TestCase):
    """Tests Watchdog manual tool loop, error surfacing, and customer/evidence tracking."""

    def test_watchdog_surfaces_gemini_error_instead_of_generic_empty(self):
        core = IntelligenceCore()
        mock_gemini = MagicMock()
        mock_gemini.is_live.return_value = True
        mock_gemini.client = MagicMock()
        mock_gemini.generate_with_tools.return_value = None
        mock_gemini.last_error = "404 NOT_FOUND: models/gemini-2.5-pro is not found"
        core.gemini = mock_gemini

        outcome = core.run_autonomous_watchdog_investigation(max_iterations=3)
        self.assertEqual(outcome["status"], "FAILED")
        self.assertIn("404 NOT_FOUND", outcome["error"])

    def test_watchdog_manual_tool_loop_retrieves_customers_and_validates(self):
        core = IntelligenceCore()
        mock_gemini = MagicMock()
        mock_gemini.is_live.return_value = True
        mock_gemini.client = MagicMock()

        # Turn 1: Gemini requests list_customer_records
        fc1 = MagicMock()
        fc1.name = "list_customer_records"
        fc1.args = {"skip": 0, "limit": 15}
        resp1 = MagicMock()
        resp1.function_calls = [fc1]
        resp1.candidates = [MagicMock(content=MagicMock())]

        # Turn 2: Gemini requests get_customer_360_profile
        fc2 = MagicMock()
        fc2.name = "get_customer_360_profile"
        fc2.args = {"customer_id_or_code": "cust-1"}
        resp2 = MagicMock()
        resp2.function_calls = [fc2]
        resp2.candidates = [MagicMock(content=MagicMock())]

        # Turn 3: Gemini returns empty validated JSON array []
        resp3 = MagicMock()
        resp3.function_calls = []
        resp3.text = "[]"
        resp3.candidates = [MagicMock(content=MagicMock())]

        mock_gemini.generate_with_tools.side_effect = [resp1, resp2, resp3]
        core.gemini = mock_gemini

        mock_registry = MagicMock()
        mock_registry.get_watchdog_callables.return_value = [lambda: None]
        mock_registry.get_watchdog_tool_names.return_value = [
            "list_customer_records",
            "get_customer_360_profile",
        ]

        def _exec(name, args, allowed_tools=None):
            if name == "list_customer_records":
                return {"customers": [{"customer_id": "cust-1"}], "limit": 15}
            if name == "get_customer_360_profile":
                return {"customer_id": "cust-1", "customer_code": "CUST-1001"}
            return {}

        mock_registry.execute_tool.side_effect = _exec
        core.registry = mock_registry

        outcome = core.run_autonomous_watchdog_investigation(max_iterations=5)
        self.assertEqual(outcome["status"], "COMPLETED")
        self.assertTrue(outcome["pagination_completed"])
        self.assertEqual(outcome["customers_retrieved_ids"], ["cust-1"])
        self.assertEqual(outcome["customers_investigated_ids"], ["cust-1"])
        self.assertEqual(len(outcome["tool_calls"]), 2)


class TestDocumentationFileServing(unittest.TestCase):
    """Tests safe PDF file retrieval for frontend display."""

    def test_get_document_file_info_enforces_upload_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_file = Path(tmpdir) / "doc-1.pdf"
            pdf_file.write_bytes(b"%PDF-1.4 sample")

            mock_doc = MagicMock()
            mock_doc.id = "doc-1"
            mock_doc.document_name = "Motor_Policy.pdf"
            mock_doc.file_location = str(pdf_file)

            mock_session = MagicMock()
            mock_session.execute.return_value.scalars.return_value.first.return_value = mock_doc

            svc = RAGService()
            with patch("app.rag.rag_service.settings") as mock_settings:
                mock_settings.RAG_UPLOAD_DIR = tmpdir
                info = svc.get_document_file_info("doc-1", db=mock_session)
                self.assertEqual(info["document_name"], "Motor_Policy.pdf")
                self.assertEqual(Path(info["file_path"]).resolve(), pdf_file.resolve())


if __name__ == "__main__":
    unittest.main(verbosity=2)
