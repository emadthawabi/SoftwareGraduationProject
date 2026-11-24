"""Generate resumable Gemini document embeddings. Preview unless --write is given."""

import argparse
import hashlib
import json
import math
import os
import time

from legal_rag.db import connect
from legal_rag.validate_tokens import SAFE_LIMITS, GeminiCounter, read_database

MODEL = "gemini-embedding-001"
DIMENSIONS = 1536
PROFILE = ("google", MODEL, DIMENSIONS, "RETRIEVAL_DOCUMENT", "l2", "gemini-retrieval-v1")
PROFILE_FILTER = """provider = %s AND model = %s AND dimensions = %s
    AND task_type = %s AND normalization = %s AND request_version = %s"""


def select_chunks(chunks, limit=None):
    """Keep the same deterministic source selection on repeated limited runs."""
    selected = [c for c in chunks if c["embedding_ready"] and c["source_searchable"]]
    if limit is not None:
        selected = selected[:limit]
    for chunk in selected:
        text = chunk["embedding_input"]
        if not text.strip() or hashlib.sha256(text.encode("utf-8")).hexdigest() != chunk["input_hash"]:
            raise ValueError("Empty input or stale input hash; rebuild chunks before embedding.")
    return selected


def normalize_vector(values):
    if values is None or len(values) != DIMENSIONS:
        raise ValueError("Unexpected embedding dimensions; batch was not saved.")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
           for v in values):
        raise ValueError("Embedding contains invalid numbers; batch was not saved.")
    length = math.hypot(*values)
    if not math.isfinite(length) or length == 0:
        raise ValueError("Embedding has invalid length; batch was not saved.")
    return [v / length for v in values]


def retry_call(call, sleep=time.sleep):
    """Retry only transient HTTP responses; never print provider error payloads."""
    for attempt in range(4):
        try:
            return call()
        except Exception as exc:
            if getattr(exc, "code", None) not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
            delay = 2 ** (attempt + 1)
            print(f"Temporary API error; retrying in {delay}s.", flush=True)
            sleep(delay)


def pending_chunks(chunks):
    with connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        hashes = {row[0] for row in conn.execute(
            "SELECT input_hash FROM embedding_cache WHERE " + PROFILE_FILTER, PROFILE)}
    # Identical inputs need only one API request and one cache entry.
    return list({c["input_hash"]: c for c in chunks if c["input_hash"] not in hashes}.values())


def generate_batch(client, chunks):
    from google.genai import types

    counter = GeminiCounter(client, MODEL)
    counts = [retry_call(lambda c=c: counter.count(c["embedding_input"])) for c in chunks]
    if any(not 0 < count <= SAFE_LIMITS[MODEL] for count in counts):
        raise ValueError("Input exceeds the safe token limit; run token validation before continuing.")
    result = retry_call(lambda: client.models.embed_content(
        model=MODEL, contents=[c["embedding_input"] for c in chunks],
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT",
                                       output_dimensionality=DIMENSIONS)))
    embeddings = result.embeddings
    if embeddings is None or len(embeddings) != len(chunks):
        raise ValueError("Embedding response count differs from input count; batch was not saved.")
    records = []
    for chunk, count, embedding in zip(chunks, counts, embeddings, strict=True):
        if getattr(getattr(embedding, "statistics", None), "truncated", False):
            raise ValueError("Provider truncated an input; batch was not saved.")
        records.append((chunk["input_hash"], count, normalize_vector(embedding.values)))
    return records


def save_batch(records):
    # One transaction per complete validated batch. Earlier batches survive failure.
    inserted = 0
    with connect() as conn:
        for fingerprint, count, vector in records:
            inserted += conn.execute("""
                INSERT INTO embedding_cache
                    (provider, model, dimensions, task_type, normalization, request_version,
                     input_hash, token_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (provider, model, dimensions, task_type, normalization,
                             request_version, input_hash) DO NOTHING
            """, (*PROFILE, fingerprint, count, json.dumps(vector, allow_nan=False))).rowcount
    return inserted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--limit", type=int, help="Select only the first N eligible chunks")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--write", action="store_true", help="Call Gemini and save vectors")
    args = parser.parse_args()
    if not args.domain.strip() or args.limit is not None and args.limit < 1:
        parser.error("Domain must not be empty and limit must be positive.")
    if not 1 <= args.batch_size <= 20:
        parser.error("Batch size must be between 1 and 20.")
    if os.getenv("EMBEDDING_MODEL", MODEL) != MODEL or os.getenv("EMBEDDING_DIMENSIONS", "1536") != "1536":
        parser.error("This generator requires EMBEDDING_MODEL=gemini-embedding-001 and EMBEDDING_DIMENSIONS=1536.")
    try:
        chunks = read_database(args.domain)
        selected = select_chunks(chunks, args.limit)
        if not selected:
            raise ValueError("No eligible chunks found; check domain and chunk preparation.")
        pending = pending_chunks(selected)
        print(f"Selected {len(selected)} eligible chunks; {len(pending)} uncached unique inputs.", flush=True)
        print(f"Excluded {sum(not c['embedding_ready'] or not c['source_searchable'] for c in chunks)} held/ineligible chunks.")
        if not args.write:
            print("Preview only: no Gemini calls or database changes. Add --write to generate.")
            return
        if not pending:
            print("All selected inputs are cached. No Gemini calls needed.")
            return
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY in .env.")
        options = types.HttpOptions(timeout=30000, retry_options=types.HttpRetryOptions(attempts=1))
        saved = 0
        with genai.Client(api_key=key, http_options=options) as client:
            for start in range(0, len(pending), args.batch_size):
                if start:
                    time.sleep(1)
                batch = pending[start:start + args.batch_size]
                saved += save_batch(generate_batch(client, batch))
                print(f"Processed {start + len(batch)}/{len(pending)} inputs; saved {saved} new vectors.", flush=True)
        print("Completed. Rerunning reuses cached vectors.")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except KeyboardInterrupt:
        raise SystemExit("Interrupted. Committed batches are safe; rerun the same command to resume.") from None
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Embedding failed ({type(exc).__name__}, code={getattr(exc, 'code', None)}). "
                         "Check migration 006, database access, API key and quota. "
                         "Committed batches are safe; rerun to resume.") from None


if __name__ == "__main__":
    main()
