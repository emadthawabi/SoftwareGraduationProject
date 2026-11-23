"""Opt-in PostgreSQL migration checks; every fixture/schema is rolled back.

PowerShell: $env:LEGAL_RAG_TEST_DATABASE='1'
python -m unittest discover -s tests -p test_embedding_storage.py -v
"""

import os
import unittest
import uuid
from pathlib import Path


@unittest.skipUnless(os.getenv("LEGAL_RAG_TEST_DATABASE") == "1", "Requires opt-in live PostgreSQL")
class EmbeddingStorageTests(unittest.TestCase):
    def test_storage_constraints_cache_survival_and_current_chunk_view(self):
        import psycopg
        from psycopg import sql

        from legal_rag.db import connect

        migration = Path(__file__).resolve().parents[1] / "database/migrations/006_embedding_storage.sql"
        vector = "[" + ",".join(["1"] + ["0"] * 1535) + "]"
        zeros = "[" + ",".join(["0"] * 1536) + "]"
        original_hash = "a" * 64
        with connect() as conn:
            # Unique isolated namespace; rollback removes it even on test failure.
            try:
                namespace = "test_embedding_" + uuid.uuid4().hex
                conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(namespace)))
                conn.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(namespace)))
                conn.execute("CREATE TABLE legislation (maqam_id integer PRIMARY KEY, domain text, superseded_by integer, jurisdiction text)")
                conn.execute("CREATE TABLE units (unit_id text PRIMARY KEY, maqam_id integer, searchable boolean)")
                conn.execute("CREATE TABLE chunks (chunk_id text PRIMARY KEY, unit_id text, input_hash text, embedding_ready boolean)")
                conn.execute(migration.read_text(encoding="utf-8"))

                def insert(value=vector, fingerprint=original_hash, model="gemini-embedding-001", dimensions=1536):
                    return conn.execute("""INSERT INTO embedding_cache
                        (provider, model, dimensions, input_hash, token_count, embedding)
                        VALUES ('google', %s, %s, %s, 100, %s::vector) RETURNING id""",
                                        (model, dimensions, fingerprint, value)).fetchone()[0]

                first = insert()
                for changes in [{}, {"value": "[1,0]"}, {"value": zeros},
                                {"fingerprint": "bad-hash"}, {"dimensions": 768}]:
                    with self.assertRaises(psycopg.Error):
                        with conn.transaction():
                            insert(**changes)
                self.assertNotEqual(first, insert(model="another-model"))
                conn.execute("INSERT INTO legislation VALUES (1, 'labour', NULL, 'unknown')")
                conn.execute("INSERT INTO units VALUES ('unit1', 1, TRUE)")
                conn.execute("INSERT INTO chunks VALUES ('chunk1', 'unit1', %s, TRUE)", (original_hash,))
                self.assertEqual(conn.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0], 2)
                conn.execute("UPDATE chunks SET input_hash = %s", ("b" * 64,))
                self.assertEqual(conn.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0], 0)
                conn.execute("UPDATE chunks SET input_hash = %s, embedding_ready = FALSE", (original_hash,))
                self.assertEqual(conn.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0], 0)
                conn.execute("DELETE FROM chunks")
                self.assertEqual(conn.execute("SELECT count(*) FROM embedding_cache").fetchone()[0], 2)
                conn.execute("INSERT INTO chunks VALUES ('rebuilt', 'unit1', %s, TRUE)", (original_hash,))
                self.assertEqual(conn.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0], 2)
                conn.execute("UPDATE units SET searchable = FALSE")
                self.assertEqual(conn.execute("SELECT count(*) FROM chunk_embeddings").fetchone()[0], 0)
            finally:
                conn.rollback()


if __name__ == "__main__":
    unittest.main()
