"""Paragraph extraction preserves wording and safe boundaries for legal chunks."""

import copy
import unittest
from pathlib import Path

from legal_rag.chunk import segments
from legal_rag.load import read_jsonl
from legal_rag.paragraphs import extract


def unit(text, title=None):
    return {"text": text, "article_title": title, "flags": ["paragraphs_not_extracted"],
            "verification": "verified_html"}


class ParagraphTests(unittest.TestCase):
    def test_intro_and_nested_list_stay_with_numeric_parent(self):
        original = unit("Intro:\n1. First clause:\nأ. Child one.\nب. Child two.\n2. Second clause.")
        before = copy.deepcopy(original)
        result = extract(original)
        self.assertEqual(original, before)
        self.assertEqual(result["lead_in"], "Intro:")
        self.assertEqual([p["label"] for p in result["paragraphs"]], ["1", "2"])
        self.assertEqual(len(result["paragraphs"][0]["items"]), 2)
        prefix, spans, _, warning = segments(result)
        self.assertIsNone(warning)
        self.assertEqual(prefix + "".join(spans), original["text"])
        self.assertIn("Child two.", spans[0])

    def test_reversed_marker_alignment_preserves_source(self):
        result = extract(unit(".1 First.\n.2 Second."))
        self.assertEqual(result["paragraph_kind"], "numbered")
        prefix, spans, _, warning = segments(result)
        self.assertIsNone(warning)
        self.assertEqual(prefix + "".join(spans), result["text"])
        self.assertTrue(spans[1].startswith(".2"))

    def test_definitions_keep_intro_and_wrapped_body(self):
        original = unit("المعاني:\nالوزارة: نص التعريف\nتكملة النص.\nالوزير: تعريف آخر.", "تعاريف")
        result = extract(original)
        self.assertEqual(result["paragraph_kind"], "definitions")
        self.assertEqual([p["label"] for p in result["paragraphs"]], ["الوزارة", "الوزير"])
        self.assertIn("تكملة النص.", result["paragraphs"][0]["text"])

    def test_missing_or_repeated_numbers_are_not_invented(self):
        for text in ["1. First\n3. Third", "2. Second\n3. Third", "1. First\n1. Another"]:
            result = extract(unit(text))
            self.assertEqual(result["paragraphs"], [])
            self.assertIn("paragraph_structure_review", result["flags"])
            self.assertEqual(result["text"], text)

    def test_duplicate_and_bare_markers_preserve_wording_and_alignment(self):
        text = "1 .1 First.\n.2 Second.\n3 Third."
        result = extract(unit(text))
        self.assertEqual([p["label"] for p in result["paragraphs"]], ["1", "2", "3"])
        prefix, spans, _, warning = segments(result)
        self.assertIsNone(warning)
        self.assertEqual(prefix + "".join(spans), text)

    def test_all_local_company_units_preserve_text_hash_and_verification(self):
        path = Path(__file__).resolve().parents[1] / "data/corpus/companies/units.jsonl"
        if not path.exists():
            self.skipTest("Local companies corpus is not supplied")
        for original in read_jsonl(path):
            with self.subTest(unit_id=original["unit_id"]):
                result = extract(original)
                for key in ["text", "sha256", "verification", "unit_id"]:
                    self.assertEqual(result[key], original[key])
                self.assertEqual(extract(result), result)
                if len(result["paragraphs"]) > 1:
                    prefix, spans, _, warning = segments(result)
                    self.assertIsNone(warning)
                    self.assertEqual(prefix + "".join(spans), original["text"])


if __name__ == "__main__":
    unittest.main()
