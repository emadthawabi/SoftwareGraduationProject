"""Combine keyword and Gemini semantic rankings using reciprocal rank fusion."""

import argparse
import json
import os
from pathlib import Path

from legal_rag.search import query_terms, search
from legal_rag.semantic_search import embed_question, retrieve


def fuse_rankings(keyword_results, semantic_results, limit=5, k=60):
    """Equal-weight RRF per source unit; raw scores never determine fusion.

    Keep each retriever's excerpt, since they may select different chunks of one
    article. Duplicate rows within one ranking contribute only once.
    """
    if not 1 <= limit <= 100 or k <= 0:
        raise ValueError("Limit must be between 1 and 100 and RRF k must be positive.")
    combined = {}
    for method, rows in (("keyword", keyword_results), ("semantic", semantic_results)):
        seen = set()
        for row in rows:
            unit_id = row["unit_id"]
            if unit_id in seen:
                continue
            seen.add(unit_id)
            rank = len(seen)
            if unit_id not in combined:
                combined[unit_id] = {
                    "unit_id": unit_id, "article_no": row.get("article_no"),
                    "document_title": row.get("document_title"),
                    "source_url": row.get("source_url"),
                    "full_article": row.get("full_article", row.get("text")),
                    "rrf_score": 0.0, "keyword_rank": None, "semantic_rank": None,
                    "matches": {},
                }
            result = combined[unit_id]
            result["rrf_score"] += 1 / (k + rank)
            result[f"{method}_rank"] = rank
            result["matches"][method] = {
                "chunk_id": row["chunk_id"], "matched_passage": row["matched_passage"],
                "requires_parent_context": row.get("requires_parent_context", False),
                "warnings": row.get("warnings", []),
                "original_score": row.get("score") if method == "keyword" else row.get("similarity"),
            }
    return sorted(combined.values(), key=lambda row: (-row["rrf_score"], row["unit_id"]))[:limit]


def hybrid_search(question, domain="labour", limit=5, candidates=20, *, client=None):
    """Embed once, retrieve a wider pool per method, then fuse by unit_id.

    Errors propagate: an unavailable semantic service is never silently presented
    as a successful hybrid search. Empty keyword matches are a normal result.
    """
    terms = query_terms(question)
    if not question.strip() or not domain.strip() or not 1 <= limit <= candidates <= 100:
        raise ValueError("Provide a question/domain and 1 <= limit <= candidates <= 100.")
    if len(terms) > 64:
        raise ValueError("Use at most 64 distinct search terms.")
    keyword_results = search(question, domain, candidates) if terms else []
    if client is None:
        from google import genai
        from google.genai import types

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("Set GEMINI_API_KEY in .env.")
        with genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=30000, retry_options=types.HttpRetryOptions(attempts=1))) as api:
            vector = embed_question(api, question)
    else:
        vector = embed_question(client, question)
    semantic_results = retrieve(vector, domain, candidates)
    return {
        "question": question, "domain": domain, "method": "rrf", "rrf_k": 60,
        "candidates_per_method": candidates,
        "keyword_count": len(keyword_results), "semantic_count": len(semantic_results),
        "results": fuse_rankings(keyword_results, semantic_results, limit),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--candidates", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("hybrid-results.json"))
    args = parser.parse_args()
    try:
        report = hybrid_search(args.question, args.domain, args.limit, args.candidates)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {len(report['results'])} hybrid results to {args.output}. Open it in VS Code.")
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        raise SystemExit(f"Hybrid search failed ({type(exc).__name__}, code={getattr(exc, 'code', None)}). "
                         "Check database access, Gemini key/quota and output path.") from None


if __name__ == "__main__":
    main()
