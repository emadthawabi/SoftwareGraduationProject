"""Source comparison must detect lost wording and wrong context without approval by sampling."""

import unittest

from legal_rag.verify_companies import compare, source_articles


class CompaniesVerificationTests(unittest.TestCase):
    def test_whitespace_only_changes_pass_but_words_and_punctuation_do_not(self):
        source = {"text": "Title\nClause 1. Full wording.", "part": "Part", "chapter": "Chapter",
                  "source_url": "https://example.org/1"}
        unit = {"article_title": "Title", "text": "Clause 1.\nFull wording.",
                "part": "Part", "chapter": "Chapter", "source_item_url": source["source_url"]}
        self.assertEqual(compare(unit, source), [])
        for text in ["Clause 1. Full wording", "Clause 2. Full wording.", "Full wording."]:
            with self.subTest(text=text):
                self.assertIn("body_text_mismatch", compare({**unit, "text": text}, source))
        self.assertIn("chapter_mismatch", compare({**unit, "chapter": "Another chapter"}, source))
        self.assertIn("title_boundary_mismatch", compare({**unit, "article_title": "Clause 1."}, source))

    def test_dom_boundaries_exclude_footer_and_reset_chapter_at_new_part(self):
        html = '<h5>Part 1</h5><h6>Chapter 1</h6>'
        for n in range(1, 347):
            if n == 2:
                html += '<h5>Part 2</h5>'
            html += (f'<dt><a href="/legislation/1211/item/{n}/">Article ({n})</a></dt>'
                     f'<dd><p>Title {n}<br>Body {n}</p></dd>')
        html += '<footer>Do not include this</footer>'
        html = html.replace('Body 65</p>', 'Body 65<br>المادة (66)</p>')
        articles = source_articles(html)
        self.assertEqual(len(articles), 346)
        self.assertEqual(articles[1]["chapter"], "Chapter 1")
        self.assertIsNone(articles[2]["chapter"])
        self.assertEqual(articles[346]["text"], "Title 346\nBody 346")
        self.assertEqual(articles[65]["text"], "Title 65\nBody 65")
        self.assertIn("source_artifact", articles[65])

    def test_incomplete_source_is_rejected(self):
        with self.assertRaises(ValueError):
            source_articles('<dt><a href="/legislation/1211/item/1/">Article (1)</a></dt><dd>Body</dd>')


if __name__ == "__main__":
    unittest.main()
