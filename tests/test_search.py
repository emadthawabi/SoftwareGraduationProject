import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from legal_rag.search import LOOKUP_SQL, SEARCH_SQL, lookup_article, main, query_terms, search


class SearchTests(unittest.TestCase):
    def test_exact_lookup_uses_document_and_article_parameters(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{"unit_id": "maqam:534:art:1", "text": "Full original"}]
        self.assertEqual(lookup_article(534, 1, connection=conn)[0]["unit_id"], "maqam:534:art:1")
        cursor.execute.assert_called_once_with(LOOKUP_SQL, (534, 1, "labour"))

    def test_exact_lookup_missing_article(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        self.assertEqual(lookup_article(1, 99999, connection=conn), [])

    def test_exact_lookup_validation(self):
        conn = MagicMock()
        for document, article, domain in [(0, 1, "labour"), (1, -1, "labour"),
                                          (1, 1, ""), (True, 1, "labour")]:
            with self.assertRaises(ValueError):
                lookup_article(document, article, domain, connection=conn)
        conn.cursor.assert_not_called()

    def test_cli_exact_dispatch_does_not_run_keyword_search(self):
        with patch("sys.argv", ["search", "--document", "1", "--article", "71"]), \
                patch("legal_rag.search.lookup_article", return_value=[]) as lookup, \
                patch("legal_rag.search.search") as keyword, patch("builtins.print"):
            main()
        lookup.assert_called_once_with(1, 71, "labour")
        keyword.assert_not_called()

    def test_cli_rejects_incomplete_or_mixed_modes(self):
        for arguments in [[], ["--article", "71"], ["--document", "1"],
                          ["question", "--document", "1", "--article", "71"]]:
            with patch("sys.argv", ["search", *arguments]), patch("sys.stderr"), \
                    self.assertRaises(SystemExit) as error:
                main()
            self.assertEqual(error.exception.code, 2)

    def test_file_output_preserves_original_arabic(self):
        rows = [{"text": "يدفع للعامل أجر ساعة ونصف عن كل ساعة عمل إضافية."}]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results.json"
            with patch("sys.argv", ["search", "الأجر", "--output", str(output)]), \
                    patch("legal_rag.search.search", return_value=rows), patch("builtins.print"):
                main()
            text = output.read_text(encoding="utf-8")
            self.assertEqual(json.loads(text), rows)
            self.assertIn(rows[0]["text"], text)

    def test_normalized_question_and_untrusted_values_are_parameters(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [{"unit_id": "maqam:1:art:71", "text": "Full article"}]
        result = search("إِضَافِيَّة ١٢", "labour'", 3, connection=conn)
        cursor.execute.assert_called_once_with(SEARCH_SQL, (["اضافية", "12"], "labour'", 3))
        self.assertEqual(result[0]["text"], "Full article")

    def test_no_matches(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        self.assertEqual(search("unknown", connection=conn), [])

    def test_question_words_removed_without_losing_negation_or_numbers(self):
        self.assertEqual(query_terms("هل لا يجوز العمل ١٢ ساعة؟"), ["لا", "يجوز", "العمل", "12", "ساعة"])
        self.assertEqual(query_terms("كم ساعة عمل إضافية يسمح بها في الأسبوع؟"),
                         ["ساعة", "عمل", "اضافية", "يسمح", "الاسبوع"])
        self.assertEqual(query_terms("ليس العمل العمل 12.5"), ["ليس", "العمل", "12.5"])

    def test_query_operators_are_not_passed_as_syntax(self):
        self.assertEqual(query_terms("الأجر | !العامل:*"), ["الاجر", "العامل"])

    def test_invalid_inputs_do_not_access_database(self):
        conn = MagicMock()
        for question, domain, limit in [(" ", "labour", 5), ("؟!", "labour", 5),
                                        ("هل كيف كم", "labour", 5),
                                        ("term", "", 5), ("term", "labour", 0),
                                        ("term", "labour", 101)]:
            with self.assertRaises(ValueError):
                search(question, domain, limit, connection=conn)
        conn.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
