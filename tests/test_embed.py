"""Offline embedding safety checks; no API calls or database writes."""

import hashlib
import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from legal_rag.embed import DIMENSIONS, generate_batch, normalize_vector, retry_call, select_chunks


def chunk(text="Arabic passage", **changes):
    return {"embedding_input": text, "input_hash": hashlib.sha256(text.encode()).hexdigest(),
            "embedding_ready": True, "source_searchable": True, **changes}


class EmbedTests(unittest.TestCase):
    def test_selection_excludes_holds_and_limits_before_cache(self):
        rows = [chunk(embedding_ready=False), chunk(source_searchable=False), chunk(), chunk("second")]
        self.assertEqual(select_chunks(rows, 1), [rows[2]])

    def test_selection_rejects_corrupt_hash_and_empty_text(self):
        for row in [chunk(input_hash="bad"), chunk(" ")]:
            with self.assertRaises(ValueError):
                select_chunks([row])

    def test_normalization_and_invalid_vectors(self):
        vector = normalize_vector([3, 4] + [0] * (DIMENSIONS - 2))
        self.assertAlmostEqual(math.hypot(*vector), 1)
        self.assertEqual(vector[:2], [0.6, 0.8])
        for values in [None, [1, 2], [0] * DIMENSIONS,
                       [float("nan")] * DIMENSIONS, [float("inf")] * DIMENSIONS,
                       [True] * DIMENSIONS]:
            with self.assertRaises(ValueError):
                normalize_vector(values)

    @patch("legal_rag.embed.GeminiCounter")
    def test_batch_checks_limits_before_embedding(self, counter):
        counter.return_value.count.return_value = 2041
        client = Mock()
        with self.assertRaises(ValueError):
            generate_batch(client, [chunk()])
        client.models.embed_content.assert_not_called()

    @patch("legal_rag.embed.GeminiCounter")
    def test_batch_checks_response_and_preserves_input(self, counter):
        counter.return_value.count.return_value = 100
        client = Mock()
        vector = SimpleNamespace(values=[1] + [0] * (DIMENSIONS - 1), statistics=None)
        client.models.embed_content.return_value = SimpleNamespace(embeddings=[vector])
        row = chunk()
        records = generate_batch(client, [row])
        self.assertEqual(records[0][:2], (row["input_hash"], 100))
        self.assertEqual(client.models.embed_content.call_args.kwargs["contents"], [row["embedding_input"]])
        client.models.embed_content.return_value.embeddings = []
        with self.assertRaises(ValueError):
            generate_batch(client, [row])
        vector.statistics = SimpleNamespace(truncated=True)
        client.models.embed_content.return_value.embeddings = [vector]
        with self.assertRaises(ValueError):
            generate_batch(client, [row])

    def test_retries_transient_errors_only(self):
        error = RuntimeError("private provider payload")
        error.code = 429
        call = Mock(side_effect=[error, "ok"])
        sleep = Mock()
        self.assertEqual(retry_call(call, sleep), "ok")
        sleep.assert_called_once_with(2)
        error.code = 400
        call = Mock(side_effect=error)
        with self.assertRaises(RuntimeError):
            retry_call(call, sleep)
        self.assertEqual(call.call_count, 1)


if __name__ == "__main__":
    unittest.main()
