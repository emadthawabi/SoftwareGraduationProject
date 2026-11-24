"""Offline answer generation and citation validation checks."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from legal_rag.answer import generate_answer, prepare_sources, validate_answer

ROWS = [{"unit_id": "maqam:1:art:103", "full_article": "النص الأصلي",
         "document_title": "قانون العمل", "article_no": 103, "source_url": "https://example.org/source"}]


class AnswerTests(unittest.TestCase):
    @patch("legal_rag.answer.time.sleep")
    @patch("legal_rag.answer.random.uniform", return_value=0.5)
    def test_transient_generation_reuses_request_and_succeeds(self, jitter, sleep):
        from legal_rag.answer import generate_with_retries

        error = RuntimeError("private provider payload")
        error.code = 503
        client = Mock()
        client.models.generate_content.side_effect = [error, "success"]
        self.assertEqual(generate_with_retries(client, model="test", contents="same sources"), "success")
        self.assertEqual(client.models.generate_content.call_count, 2)
        calls = client.models.generate_content.call_args_list
        self.assertEqual(calls[0], calls[1])
        sleep.assert_called_once_with(2.5)

    @patch("legal_rag.answer.time.sleep")
    def test_permanent_errors_do_not_retry_and_transient_attempts_are_bounded(self, sleep):
        from legal_rag.answer import generate_with_retries

        for code, attempts in [(400, 1), (401, 1), (403, 1), (429, 1), (503, 4)]:
            error = RuntimeError("private provider payload")
            error.code = code
            client = Mock()
            client.models.generate_content.side_effect = error
            with self.assertRaises(RuntimeError):
                generate_with_retries(client, model="test", contents="same sources")
            self.assertEqual(client.models.generate_content.call_count, attempts)

    @patch("legal_rag.answer.request_completion")
    def test_empty_sources_abstain_without_api(self, request):
        result = generate_answer("سؤال", [])
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["sources"], [])
        request.assert_not_called()

    @patch("legal_rag.answer.request_completion")
    def test_answer_preserves_source_and_renders_verified_citation(self, request):
        request.return_value = {"status": "answered", "claims": [
            {"text": "إجابة", "source_ids": ["maqam:1:art:103"]}], "limitation": ""}
        result = generate_answer("سؤال", ROWS, key="fake-test-key")
        self.assertIn("[maqam:1:art:103]", result["answer"])
        self.assertEqual(result["sources"][0]["source_url"], ROWS[0]["source_url"])
        self.assertEqual(request.call_args.args[1]["maqam:1:art:103"]["text"], "النص الأصلي")

    def test_invalid_citations_and_missing_evidence_are_rejected(self):
        sources = prepare_sources(ROWS)
        for answer in [
            {"status": "answered", "claims": [], "limitation": ""},
            {"status": "answered", "claims": [{"text": "نص", "source_ids": ["invented"]}], "limitation": ""},
            {"status": "answered", "claims": [{"text": "نص", "source_ids": []}], "limitation": ""},
            {"status": "partial", "claims": [{"text": "نص", "source_ids": ["maqam:1:art:103"]}], "limitation": ""},
            {"status": "insufficient", "claims": [], "limitation": ""},
        ]:
            with self.assertRaises(ValueError):
                validate_answer(answer, sources)

    def test_context_is_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            prepare_sources([{**ROWS[0], "full_article": "x" * 18001}])

    @patch("legal_rag.answer.genai.Client")
    def test_request_uses_json_schema_and_rejects_incomplete_output(self, client_factory):
        from legal_rag.answer import request_completion

        client = client_factory.return_value.__enter__.return_value
        client.models.generate_content.return_value = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")], text="{}")
        with self.assertRaises(ValueError):
            request_completion("سؤال", prepare_sources(ROWS), "fake-test-key")
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.response_mime_type, "application/json")
        self.assertIn("claims", config.response_json_schema["properties"])

    @patch("legal_rag.answer.genai.Client")
    def test_complete_response_and_configurable_model(self, client_factory):
        from legal_rag.answer import request_completion

        client = client_factory.return_value.__enter__.return_value
        client.models.generate_content.return_value = SimpleNamespace(
            candidates=[SimpleNamespace(finish_reason="STOP")],
            text='{"status":"insufficient","claims":[],"limitation":"missing"}')
        with patch.dict("os.environ", {"ANSWER_MODEL": "test-gemini-model"}):
            result = request_completion("سؤال", prepare_sources(ROWS), "fake-test-key")
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(client.models.generate_content.call_args.kwargs["model"], "test-gemini-model")


if __name__ == "__main__":
    unittest.main()
