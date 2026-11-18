"""Read-only embedding token preflight; no embeddings or model API calls."""

import argparse
import hashlib
import json
from pathlib import Path

MODEL_LIMITS = {"text-embedding-3-small": 8192, "text-embedding-3-large": 8192}


def validate_chunks(chunks, model="text-embedding-3-small", max_tokens=None, *, encoding=None):
    """Count EXACT embedding_input, including headings; preserve preparation holds.

    encoding is injectable for offline boundary tests. Production always uses the
    selected model's tokenizer, with special-looking source strings treated as text.
    No truncation, splitting, input normalization or database writes occur here.
    """
    if model not in MODEL_LIMITS:
        raise ValueError(f"Unsupported embedding model: {model}")
    limit = MODEL_LIMITS[model] if max_tokens is None else max_tokens
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MODEL_LIMITS[model]:
        raise ValueError(f"Token limit must be between 1 and {MODEL_LIMITS[model]}.")
    if encoding is None:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
    rows = []
    for chunk in chunks:
        text = chunk["embedding_input"]
        count = len(encoding.encode(text, disallowed_special=()))
        token_status = "empty" if not text.strip() else "too_long" if count > limit else "within_limit"
        hash_matches = hashlib.sha256(text.encode("utf-8")).hexdigest() == chunk["input_hash"]
        held = not chunk["embedding_ready"] or not chunk.get("source_searchable", True)
        rows.append({
            "chunk_id": chunk["chunk_id"],
            "unit_id": chunk["unit_id"],
            "input_hash": chunk["input_hash"],
            "token_count": count,
            "token_status": token_status,
            "held_for_review": held,
            "input_hash_matches": hash_matches,
            "can_embed": token_status == "within_limit" and not held and hash_matches,
            "requires_parent_context": chunk.get("requires_parent_context", False),
            "warnings": chunk.get("warnings", []),
        })
    return {
        "model": model,
        "encoding": encoding.name,
        "token_limit": limit,
        "total_chunks": len(rows),
        "can_embed": sum(row["can_embed"] for row in rows),
        "held_for_review": sum(row["held_for_review"] for row in rows),
        "too_long": sum(row["token_status"] == "too_long" for row in rows),
        "empty_inputs": sum(row["token_status"] == "empty" for row in rows),
        "hash_mismatches": sum(not row["input_hash_matches"] for row in rows),
        "max_token_count": max((row["token_count"] for row in rows), default=0),
        "max_candidate_token_count": max((row["token_count"] for row in rows if not row["held_for_review"]), default=0),
        "candidate_total_tokens": sum(row["token_count"] for row in rows if row["can_embed"]),
        "chunks": rows,
    }


def read_database(domain):
    from psycopg.rows import dict_row

    from legal_rag.db import connect

    with connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT c.chunk_id, c.unit_id, c.embedding_input, c.input_hash,
                       c.embedding_ready, c.requires_parent_context, c.warnings,
                       (u.searchable AND l.superseded_by IS NULL
                        AND l.jurisdiction IS DISTINCT FROM 'repealed') AS source_searchable
                FROM chunks c JOIN units u ON u.unit_id = c.unit_id
                JOIN legislation l ON l.maqam_id = u.maqam_id
                WHERE l.domain = %s ORDER BY c.unit_id, c.chunk_index
            """, (domain,))
            return list(cur.fetchall())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--source", choices=("database", "corpus"), default="database")
    parser.add_argument("--model", choices=tuple(MODEL_LIMITS), default="text-embedding-3-small")
    parser.add_argument("--max-tokens", type=int, help="Optional stricter limit, never above model maximum")
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON report with every chunk count")
    args = parser.parse_args()
    if not args.domain.strip():
        parser.error("Domain must not be empty.")
    if args.max_tokens is not None and not 1 <= args.max_tokens <= MODEL_LIMITS[args.model]:
        parser.error(f"--max-tokens must be between 1 and {MODEL_LIMITS[args.model]}.")
    try:
        if args.source == "corpus":
            from legal_rag.chunk import prepare, read_corpus
            chunks = prepare(read_corpus(Path("data/corpus") / args.domain), args.domain, 1500)
        else:
            chunks = read_database(args.domain)
        if not chunks:
            raise SystemExit("No chunks found; check domain, migrations and chunk generation.")
        report = validate_chunks(chunks, args.model, args.max_tokens)
    except ModuleNotFoundError as exc:
        raise SystemExit(f"Missing dependency {exc.name}. Run: python -m pip install -r requirements.txt") from None
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        # Avoid leaking connection settings through driver errors.
        raise SystemExit(f"Validation failed ({type(exc).__name__}). Check PostgreSQL/configuration "
                         "or tokenizer availability; first tokenizer use may need internet access.") from None
    report["source"] = args.source
    report["domain"] = args.domain
    print(json.dumps({key: value for key, value in report.items() if key != "chunks"}, indent=2))
    print("Held chunks:", [row["chunk_id"] for row in report["chunks"] if row["held_for_review"]])
    print("Oversized chunks:", [row["chunk_id"] for row in report["chunks"] if row["token_status"] == "too_long"])
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved report to {args.output}")
    # Holds are expected; invalid eligible inputs require attention before API use.
    if any(not row["held_for_review"] and not row["can_embed"] for row in report["chunks"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
