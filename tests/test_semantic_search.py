"""Question embedding safety and retrieval query checks without API calls."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from legal_rag.embed import DIMENSIONS, PROFILE
from legal_rag.semantic_search import embed_question, retrieve


class SemanticSearchTests(unittest.TestCase):
    @patch("legal_rag.semantic_search.GeminiCounter")
    def test_query_uses_matching_model_dimensions_and_query_task(self, counter):
        counter.return_value.count.return_value = 20
        client = Mock()
        client.models.embed_content.return_value.embeddings = [
            SimpleNamespace(values=[2] + [0] * (DIMENSIONS - 1), statistics=None)]
        vector = embed_question(client, "سؤال عن العمل")
        self.assertEqual(vector[0], 1)
        options = client.models.embed_content.call_args.kwargs
        self.assertEqual(options["config"].task_type, "RETRIEVAL_QUERY")
        self.assertEqual(options["config"].output_dimensionality, DIMENSIONS)
        self.assertEqual(options["contents"], "سؤال عن العمل")
        counter.return_value.count.return_value = 2041
        client.models.embed_content.reset_mock()
        with self.assertRaises(ValueError):
            embed_question(client, "too long")
        client.models.embed_content.assert_not_called()

    def test_invalid_inputs_do_not_access_database(self):
        with patch("legal_rag.semantic_search.connect") as connect:
            with self.assertRaises(ValueError):
                retrieve([1, 2])
            with self.assertRaises(ValueError):
                retrieve([], limit=0)
            connect.assert_not_called()

    @patch("legal_rag.semantic_search.connect")
    def test_read_only_retrieval_filters_full_document_profile(self, connect):
        conn = connect.return_value.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []
        self.assertEqual(retrieve([1] + [0] * (DIMENSIONS - 1)), [])
        conn.execute.assert_called_once_with("SET TRANSACTION READ ONLY")
        query, params = cur.execute.call_args.args
        self.assertIn("<=>", query)
        self.assertIn("unit_rank = 1", query)
        self.assertEqual(params[3:9], PROFILE)


if __name__ == "__main__":
    unittest.main()
