import copy
import hashlib
import unittest

from legal_rag.validate_tokens import validate_chunks


class CharacterEncoder:
    """Known counts for exact boundary tests, NOT a production tokenizer."""

    name = "test-character-encoder"

    def encode(self, text, *, disallowed_special):
        assert disallowed_special == ()
        return list(text)


def chunk(text, ready=True):
    return {
        "chunk_id": "maqam:1:art:1:chunk:0", "unit_id": "maqam:1:art:1",
        "embedding_input": text, "embedding_ready": ready,
        "input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


class TokenTests(unittest.TestCase):
    def test_real_model_tokenizer_handles_arabic_and_special_looking_text(self):
        import tiktoken

        text = "المادة 71: الأجر <|endoftext|>"
        result = validate_chunks([chunk(text)])
        encoder = tiktoken.encoding_for_model("text-embedding-3-small")
        self.assertEqual(result["encoding"], "cl100k_base")
        self.assertEqual(result["chunks"][0]["token_count"], len(encoder.encode_ordinary(text)))
        self.assertEqual(result["can_embed"], 1)

    def test_limit_boundary_and_header_are_counted(self):
        rows = [chunk("head\nbody"), chunk("head\nbody!")]
        result = validate_chunks(rows, max_tokens=9, encoding=CharacterEncoder())
        self.assertEqual([r["token_count"] for r in result["chunks"]], [9, 10])
        self.assertEqual(result["can_embed"], 1)
        self.assertEqual(result["too_long"], 1)

    def test_hold_is_not_removed_by_small_token_count(self):
        report = validate_chunks([chunk("table", False)], encoding=CharacterEncoder())
        self.assertEqual(report["held_for_review"], 1)
        self.assertEqual(report["can_embed"], 0)
        self.assertEqual(report["chunks"][0]["token_status"], "within_limit")

    def test_empty_stale_hash_and_ineligible_source(self):
        stale = chunk("text")
        stale["input_hash"] = "incorrect"
        excluded = chunk("text")
        excluded["source_searchable"] = False
        report = validate_chunks([chunk("  "), stale, excluded], encoding=CharacterEncoder())
        self.assertEqual(report["can_embed"], 0)
        self.assertEqual(report["empty_inputs"], 1)
        self.assertEqual(report["hash_mismatches"], 1)

    def test_validation_does_not_change_originals(self):
        rows = [chunk("المادة ١: الأجر <|endoftext|>")]
        before = copy.deepcopy(rows)
        validate_chunks(rows, encoding=CharacterEncoder())
        self.assertEqual(rows, before)

    def test_reject_unsupported_model_and_invalid_limits(self):
        with self.assertRaises(ValueError):
            validate_chunks([], model="unknown", encoding=CharacterEncoder())
        for limit in [0, -1, 8193, True]:
            with self.assertRaises(ValueError):
                validate_chunks([], max_tokens=limit, encoding=CharacterEncoder())


if __name__ == "__main__":
    unittest.main()
