"""Nested company excerpts retain the entire governing introductory wording."""

import unittest

from legal_rag.chunk import nested_passages


class NestedChunkTests(unittest.TestCase):
    def test_intro_repeated_and_nested_items_not_orphaned(self):
        prefix = "ARTICLE CONDITION\n"
        intro = "1. PARENT CONDITION:\n"
        first = "أ. " + "First clause. " * 4 + "\n"
        second = "ب. " + "Second clause. " * 4 + "\n"
        chunks = nested_passages(intro + first + second, prefix, 120)
        self.assertEqual(chunks, [prefix + intro + first, prefix + intro + second])
        self.assertTrue(all(len(c) <= 120 for c in chunks))

    def test_grandchildren_keep_parent_and_child_conditions(self):
        intro = "1. Main condition:\n"
        child = "أ. Child condition:\n"
        one = "1) " + "Alpha. " * 7 + "\n"
        two = "2) " + "Beta. " * 7 + "\n"
        chunks = nested_passages(intro + child + one + two, "", 110)
        self.assertEqual(chunks, [intro + child + one, intro + child + two])

    def test_atomic_oversized_clause_is_not_cut(self):
        text = "1. Rule:\nأ. " + "x" * 200
        self.assertEqual(nested_passages(text, "", 50), [text])


if __name__ == "__main__":
    unittest.main()
