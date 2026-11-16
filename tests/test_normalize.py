import unittest

from legal_rag.normalize import normalize_search_text


class NormalizationTests(unittest.TestCase):
    def test_arabic_spelling_marks_and_digits(self):
        self.assertEqual(normalize_search_text("إِجَازَة   سَنَوِيَّة ١٤"), "اجازة سنوية 14")

    def test_legal_distinctions_and_numbers_are_preserved(self):
        text = "لا يجوز 12.5% إلى ٣٠ درجة ½"
        self.assertEqual(normalize_search_text(text), "لا يجوز 12.5% الى 30 درجة ½")
        self.assertNotEqual(normalize_search_text("شركة"), normalize_search_text("شركه"))

    def test_idempotent(self):
        text = normalize_search_text("الأَجْـر ۱۲\n ABC")
        self.assertEqual(normalize_search_text(text), text)


if __name__ == "__main__":
    unittest.main()
