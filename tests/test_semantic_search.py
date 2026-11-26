"""Question embedding safety and retrieval query checks without API calls."""

import os
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

    @unittest.skipUnless(os.getenv("LEGAL_RAG_TEST_DATABASE") == "1",
                         "Requires opt-in live PostgreSQL")
    def test_all_scope_reads_existing_vectors_and_specific_scope_stays_filtered(self):
        import json

        from legal_rag.db import connect
        from legal_rag.embed import PROFILE_FILTER

        with connect() as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            samples = conn.execute("SELECT DISTINCT ON (domain) domain, embedding::text "
                                   "FROM chunk_embeddings WHERE " + PROFILE_FILTER +
                                   " ORDER BY domain, chunk_id", PROFILE).fetchall()
        if not samples:
            self.skipTest("No current-profile vectors available")
        for domain, encoded in samples:
            vector = json.loads(encoded)
            all_rows = retrieve(vector, "all", 5)
            self.assertTrue(all_rows, "all must not be interpreted as a literal domain")
            self.assertTrue(any(row["domain"] == domain for row in all_rows))
            specific_rows = retrieve(vector, domain, 5)
            self.assertTrue(specific_rows)
            self.assertTrue(all(row["domain"] == domain for row in specific_rows))


if __name__ == "__main__":
    unittest.main()
