"""Embed a question and retrieve legal passages by cosine similarity."""

import argparse
import json
import os
from pathlib import Path

from psycopg.rows import dict_row

from legal_rag.db import connect
from legal_rag.embed import DIMENSIONS, MODEL, PROFILE, normalize_vector, retry_call
from legal_rag.validate_tokens import GeminiCounter, SAFE_LIMITS


def embed_question(client, question):
    from google.genai import types

    if not question.strip():
        raise ValueError("Question must not be empty.")
    count = retry_call(lambda: GeminiCounter(client, MODEL).count(question))
    if not 0 < count <= SAFE_LIMITS[MODEL]:
        raise ValueError("Question exceeds the safe token limit.")
    response = retry_call(lambda: client.models.embed_content(
        model=MODEL, contents=question,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY",
                                       output_dimensionality=DIMENSIONS)))
    if not response.embeddings or len(response.embeddings) != 1:
        raise ValueError("Expected exactly one question embedding.")
    embedding = response.embeddings[0]
    if getattr(getattr(embedding, "statistics", None), "truncated", False):
        raise ValueError("Provider truncated the question.")
    return normalize_vector(embedding.values)


def retrieve(vector, domain="labour", limit=5):
    if not domain.strip() or not 1 <= limit <= 100:
        raise ValueError("Provide a domain and a limit between 1 and 100.")
    vector = normalize_vector(vector)
    with connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                WITH ranked AS (
                    SELECT c.chunk_id, c.unit_id, c.content AS matched_passage,
                           u.text AS full_article, u.article_no, l.title AS document_title,
                           c.requires_parent_context, c.warnings,
                           COALESCE(u.source_item_url, u.source_page_url, l.pdf_url) AS source_url,
                           1 - (e.embedding <=> %s::vector) AS similarity,
                           row_number() OVER (PARTITION BY c.unit_id
                               ORDER BY e.embedding <=> %s::vector, c.chunk_index) AS unit_rank
                    FROM chunk_embeddings e
                    JOIN chunks c ON c.chunk_id = e.chunk_id
                    JOIN units u ON u.unit_id = c.unit_id
                    JOIN legislation l ON l.maqam_id = u.maqam_id
                    WHERE e.domain = %s AND e.provider = %s AND e.model = %s
                      AND e.dimensions = %s AND e.task_type = %s
                      AND e.normalization = %s AND e.request_version = %s
                )
                SELECT chunk_id, unit_id, matched_passage, full_article, article_no,
                       document_title, requires_parent_context, warnings, source_url, similarity
                FROM ranked WHERE unit_rank = 1
                ORDER BY similarity DESC, chunk_id LIMIT %s
            """, (json.dumps(vector), json.dumps(vector), domain, *PROFILE, limit))
            return list(cur.fetchall())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("semantic-results.json"))
    args = parser.parse_args()
    if not args.question.strip() or not args.domain.strip() or not 1 <= args.limit <= 100:
        parser.error("Provide a question, domain and limit between 1 and 100.")
    try:
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY in .env.")
        with genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=30000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
            vector = embed_question(client, args.question)
        # Save the vector before retrieval so it remains available if PostgreSQL fails.
        report = {"question": args.question, "model": MODEL, "dimensions": DIMENSIONS,
                  "task_type": "RETRIEVAL_QUERY", "normalization": "l2", "vector": vector}
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["domain"] = args.domain
        report["results"] = retrieve(vector, args.domain, args.limit)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {len(vector)} vector numbers and {len(report['results'])} passages to {args.output}.")
        print("Open the JSON in VS Code; compare the question with each matched_passage/full_article.")
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except Exception as exc:
        raise SystemExit(f"Semantic search failed ({type(exc).__name__}, code={getattr(exc, 'code', None)}). "
                         "Check database access, API key, quota and output path.") from None


if __name__ == "__main__":
    main()
