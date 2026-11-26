"""Offline fusion and hybrid orchestration checks."""

import unittest
from unittest.mock import Mock, patch

from legal_rag.hybrid_search import fuse_rankings, hybrid_search


def row(unit, score=0):
    return {"unit_id": unit, "chunk_id": unit + ":chunk:0", "matched_passage": "نص",
            "text": "النص الكامل", "score": score, "similarity": score}


class HybridTests(unittest.TestCase):
    def test_semantic_rank_one_survives_cross_method_overlap_bias(self):
        keyword = [row(f"other-{i}") for i in range(10)]
        semantic = [row("relevant-registration")] + keyword
        plain = fuse_rankings(keyword, semantic, limit=5)
        self.assertNotIn("relevant-registration", [r["unit_id"] for r in plain])
        protected = fuse_rankings(keyword, semantic, limit=5, preserve_semantic_best=True)
        self.assertEqual(len(protected), 5)
        self.assertEqual(protected[:4], plain[:4])
        self.assertEqual(protected[-1]["unit_id"], "relevant-registration")
        self.assertEqual(protected[-1]["semantic_rank"], 1)
        self.assertIsNone(protected[-1]["keyword_rank"])
        self.assertAlmostEqual(protected[-1]["rrf_score"], 1 / 61)

    def test_semantic_safeguard_does_not_duplicate_or_override_single_result(self):
        rows = [row("a"), row("b")]
        self.assertEqual(fuse_rankings(rows, rows, preserve_semantic_best=True), fuse_rankings(rows, rows))
        self.assertEqual(fuse_rankings(rows, [], preserve_semantic_best=True), fuse_rankings(rows, []))
        self.assertEqual(fuse_rankings(rows, [row("other")], 1, preserve_semantic_best=True),
                         fuse_rankings(rows, [row("other")], 1))

    def test_overlap_scores_by_rank_not_raw_score(self):
        result = fuse_rankings([row("a", 10000), row("b", -1)], [row("b", -100), row("c", 100)])
        self.assertEqual(result[0]["unit_id"], "b")
        self.assertAlmostEqual(result[0]["rrf_score"], 1 / 62 + 1 / 61)
        self.assertEqual(result[0]["keyword_rank"], 2)
        self.assertEqual(result[0]["semantic_rank"], 1)
        self.assertEqual(set(result[0]["matches"]), {"keyword", "semantic"})

    def test_duplicates_contribute_once_and_preserve_different_excerpts(self):
        semantic = row("a")
        semantic["matched_passage"] = "مقطع آخر"
        result = fuse_rankings([row("a"), row("a"), row("b")], [semantic])
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["rrf_score"], 2 / 61)
        self.assertEqual(result[1]["keyword_rank"], 2)
        self.assertNotEqual(result[0]["matches"]["keyword"]["matched_passage"],
                            result[0]["matches"]["semantic"]["matched_passage"])

    def test_empty_rankings_and_ties_are_deterministic(self):
        self.assertEqual(fuse_rankings([], []), [])
        self.assertEqual(fuse_rankings([], [row("a")])[0]["semantic_rank"], 1)
        self.assertEqual([r["unit_id"] for r in fuse_rankings([row("b")], [row("a")])], ["a", "b"])

    @patch("legal_rag.hybrid_search.retrieve")
    @patch("legal_rag.hybrid_search.embed_question")
    @patch("legal_rag.hybrid_search.search")
    def test_embeds_once_and_uses_wider_candidate_pool(self, search, embed, retrieve):
        search.return_value = [row("a")]
        retrieve.return_value = [row("a"), row("b")]
        embed.return_value = [1]
        client = Mock()
        result = hybrid_search("حقوق العامل", limit=1, candidates=20, client=client)
        embed.assert_called_once_with(client, "حقوق العامل")
        search.assert_called_once_with("حقوق العامل", "all", 20)
        retrieve.assert_called_once_with([1], "all", 20)
        self.assertEqual(len(result["results"]), 1)

    def test_article_numbers_in_different_documents_remain_distinct(self):
        labour = {**row("maqam:1:art:5"), "domain": "labour", "article_no": 5}
        company = {**row("maqam:1211:art:5"), "domain": "companies", "article_no": 5}
        results = fuse_rankings([labour], [company])
        self.assertEqual(len(results), 2)
        self.assertEqual({r["domain"] for r in results}, {"labour", "companies"})

    @patch("legal_rag.hybrid_search.search")
    def test_invalid_options_do_not_access_services(self, search):
        for question, options in [(" ", {}), ("عمل", {"limit": 21}), ("عمل", {"candidates": 101})]:
            with self.assertRaises(ValueError):
                hybrid_search(question, **options)
        search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
