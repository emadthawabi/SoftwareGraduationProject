import copy
import unittest
from pathlib import Path

from legal_rag.chunk import build_chunks, eligible, prepare, read_corpus, segments


class ChunkTests(unittest.TestCase):
    def setUp(self):
        self.leg = {
            "title": "Document",
            "superseded_by": None,
            "jurisdiction": "unknown",
        }
        self.unit = {
            "unit_id": "maqam:10:art:1",
            "kind": "article",
            "article_no": 1,
            "verification": "verified_html",
            "text": "Intro: 1- Alpha. 2- Beta.",
            "paragraphs": [
                {"label": "1", "text": "Alpha."},
                {"label": "2", "text": "Beta."},
            ],
        }

    def test_short_article_is_exact(self):
        chunk, = build_chunks(self.unit, self.leg, "labour")
        self.assertEqual(chunk["content"], self.unit["text"])
        self.assertIn("Document", chunk["context_header"])

    def test_inline_paragraphs_preserve_prefix_and_labels(self):
        chunks = build_chunks(self.unit, self.leg, "labour", 17)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[1]["content"], "Intro: 2- Beta.")
        self.assertEqual(chunks[1]["paragraph_labels"], ["2"])

    def test_nested_items_stay_with_parent(self):
        self.unit["text"] = "Intro: 1- Alpha. a) child. 2- Beta."
        self.unit["paragraphs"][0]["items"] = [{"label": "a", "text": "child."}]
        chunks = build_chunks(self.unit, self.leg, "labour", 17)
        self.assertIn("a) child.", chunks[0]["content"])
        self.assertNotIn("child", chunks[1]["content"])

    def test_unaligned_structure_falls_back_without_loss(self):
        self.unit["paragraphs"][0]["text"] = "not in source"
        chunk, = build_chunks(self.unit, self.leg, "labour", 10)
        self.assertEqual(chunk["content"], self.unit["text"])
        self.assertIn("paragraph_alignment_failed", chunk["warnings"])

    def test_attachment_is_not_cut(self):
        self.unit["kind"] = "attachment"
        chunk, = build_chunks(self.unit, self.leg, "labour", 10)
        self.assertEqual(chunk["content"], self.unit["text"])
        self.assertIn("attachment_structure_review", chunk["warnings"])

    def test_exclusions(self):
        for field, value in [("verification", "flagged"), ("kind", "preamble")]:
            unit = dict(self.unit, **{field: value})
            self.assertEqual(build_chunks(unit, self.leg, "labour"), [])
        self.assertEqual(build_chunks(self.unit, dict(self.leg, superseded_by=20), "labour"), [])
        self.assertEqual(build_chunks(self.unit, dict(self.leg, jurisdiction="repealed"), "labour"), [])

    def test_repeatable_and_no_mutation(self):
        before = copy.deepcopy(self.unit)
        first = build_chunks(self.unit, self.leg, "labour", 17)
        self.assertEqual(first, build_chunks(self.unit, self.leg, "labour", 17))
        self.assertEqual(before, self.unit)
        changed = build_chunks(self.unit, dict(self.leg, title="Changed"), "labour", 17)
        self.assertNotEqual(first[0]["input_hash"], changed[0]["input_hash"])

    def test_real_corpus_coverage(self):
        path = Path(__file__).resolve().parents[1] / "data/corpus/labour"
        if not path.exists():
            self.skipTest("Local corpus unavailable")
        pairs = read_corpus(path)
        before = copy.deepcopy(pairs)
        chunks = prepare(pairs, "labour", 1500)
        expected = {u["unit_id"] for u, leg in pairs if eligible(u, leg)}
        self.assertEqual(len(expected), 405)
        self.assertEqual({c["unit_id"] for c in chunks}, expected)
        self.assertEqual(len({c["chunk_id"] for c in chunks}), len(chunks))
        for unit, leg in pairs:
            own = [c for c in chunks if c["unit_id"] == unit["unit_id"]]
            if not own:
                continue
            if len(own) == 1:
                self.assertEqual(own[0]["content"], unit["text"])
            else:
                prefix, spans, labels, warning = segments(unit)
                self.assertIsNone(warning)
                self.assertEqual(prefix + "".join(spans), unit["text"])
                self.assertEqual([label for c in own for label in c["paragraph_labels"]], labels)
                reconstructed = prefix + "".join(c["content"][len(prefix):] for c in own)
                self.assertEqual(reconstructed, unit["text"])
        self.assertEqual(pairs, before)
        self.assertEqual(chunks, prepare(pairs, "labour", 1500))


if __name__ == "__main__":
    unittest.main()
