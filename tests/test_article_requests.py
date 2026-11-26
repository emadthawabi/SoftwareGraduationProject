"""Ambiguous article numbers must not select a law through semantic ranking."""

import unittest
from unittest.mock import patch

from legal_rag.answer import direct_article_request


class ArticleRequestTests(unittest.TestCase):
    def test_normal_question_does_not_query_database(self):
        with patch("legal_rag.db.connect") as connect:
            self.assertIsNone(direct_article_request("ما حقوق العامل؟", "all"))
        connect.assert_not_called()

    @patch("legal_rag.db.connect")
    def test_ambiguous_number_asks_for_law(self, connect):
        cur = connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = [{"maqam_id": 1, "domain": "labour", "document_title": "Labour"},
                                    {"maqam_id": 1211, "domain": "companies", "document_title": "Companies"}]
        with patch("legal_rag.answer.lookup_article") as lookup:
            result = direct_article_request("اعطني نص المادة رقم ٥", "all")
        self.assertEqual(result["route"], "article_clarification")
        self.assertEqual(len(result["clarification_options"]), 2)
        self.assertEqual(result["claims"], [])
        lookup.assert_not_called()
        self.assertEqual(cur.execute.call_args.args[1], (5, "all"))

    @patch("legal_rag.db.connect")
    @patch("legal_rag.answer.lookup_article")
    def test_single_document_returns_original_wording(self, lookup, connect):
        conn = connect.return_value.__enter__.return_value
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            {"maqam_id": 1211, "domain": "companies", "document_title": "Companies"}]
        lookup.return_value = [{"text": "Original text.", "unit_id": "maqam:1211:art:5",
                               "document_title": "Companies", "source_url": "https://example.org"}]
        result = direct_article_request("اعطني نص المادة 5", "companies")
        self.assertEqual(result["answer"], "Original text.")
        self.assertIsNone(result["model"])
        lookup.assert_called_once_with(1211, 5, "companies", connection=conn)


if __name__ == "__main__":
    unittest.main()
