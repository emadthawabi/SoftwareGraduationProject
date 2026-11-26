"""Schema adaptation must not invent legal text or source verification."""

import unittest
from pathlib import Path

from legal_rag.load import is_searchable, read_jsonl
from legal_rag.prepare_companies import adapt


class CompaniesPreparationTests(unittest.TestCase):
    def test_actual_corpus_preserves_text_and_hold_on_repeated_adaptation(self):
        root = Path(__file__).resolve().parents[1] / "data/corpus/companies"
        if not root.exists():
            self.skipTest("Local ignored companies corpus is not supplied")
        # Test original unverified scrape even after source reviews are recorded.
        leg_path = root / "legislation.before-schema.jsonl"
        unit_path = root / "units.before-schema.jsonl"
        if not leg_path.exists() or not unit_path.exists():
            self.skipTest("Original unverified scrape backups not supplied")
        originals = read_jsonl(leg_path), read_jsonl(unit_path)
        legs, units = adapt(*originals, "2026-11-25")
        self.assertEqual([u["text"] for u in units], [u["text"] for u in originals[1]])
        self.assertEqual(len(units), 346)
        self.assertTrue(all(not is_searchable(u, legs[0]) for u in units))
        self.assertEqual(adapt(legs, units, "2026-11-25"), (legs, units))

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            adapt([{"maqam_id": 1211}, {"maqam_id": 1211}], [])


if __name__ == "__main__":
    unittest.main()
