"""Retrieve legal articles by keywords or exact document/article IDs. No model API."""

import argparse
import json
import re
import sys
from pathlib import Path

from legal_rag.normalize import normalize_search_text

# Only question/function words. Never discard negation or numeric constraints.
QUESTION_WORDS = {
    "كم", "كيف", "ما", "ماذا", "هل", "من", "هو", "هي", "في", "بها",
    "به", "عن", "على", "الى", "حسب", "الذي", "التي", "هذا", "هذه",
}


def query_terms(question: str) -> list[str]:
    normalized = normalize_search_text(question)
    tokens = re.findall(r"[^\W_]+(?:[.٫][0-9]+)?", normalized)
    return list(dict.fromkeys(term for term in tokens if term not in QUESTION_WORDS))


SEARCH_SQL = """
WITH tokens AS (
    SELECT term, plainto_tsquery('simple'::regconfig, term) AS term_query
    FROM unnest(%s::text[]) AS input(term)
), query AS (
    SELECT to_tsquery('simple'::regconfig, string_agg(quote_literal(term), ' | ')) AS terms
    FROM tokens
), matches AS (
    SELECT c.chunk_id, c.unit_id, c.content AS matched_passage,
           u.text AS text, c.requires_parent_context, c.warnings,
           l.maqam_id, l.domain, l.title AS document_title, l.number AS document_number,
           l.year AS document_year, u.article_no, u.article_title,
           COALESCE(u.source_item_url, u.source_page_url, l.pdf_url) AS source_url,
           (SELECT count(*) FROM tokens WHERE c.search_vector @@ tokens.term_query) AS matched_terms,
           ts_rank_cd(c.search_vector, query.terms) AS score,
           ROW_NUMBER() OVER (
               PARTITION BY c.unit_id
               ORDER BY (SELECT count(*) FROM tokens WHERE c.search_vector @@ tokens.term_query) DESC,
                        ts_rank_cd(c.search_vector, query.terms) DESC, c.chunk_index
           ) AS unit_rank
    FROM chunks c
    JOIN units u ON u.unit_id = c.unit_id
    JOIN legislation l ON l.maqam_id = u.maqam_id
    CROSS JOIN query
    WHERE l.domain = COALESCE(NULLIF(%s, 'all'), l.domain)
      AND u.searchable AND c.embedding_ready
      AND l.superseded_by IS NULL
      AND l.jurisdiction IS DISTINCT FROM 'repealed'
      AND c.search_vector @@ query.terms
)
SELECT chunk_id, unit_id, matched_passage, text, requires_parent_context, warnings,
       maqam_id, domain, document_title, document_number, document_year,
       article_no, article_title, source_url, matched_terms, score
FROM matches WHERE unit_rank = 1
ORDER BY matched_terms DESC, score DESC, maqam_id, article_no NULLS LAST, unit_id
LIMIT %s
"""


def search(question: str, domain: str = "labour", limit: int = 5, *, connection=None) -> list[dict]:
    """Return unique source units, with best matching excerpt and full parent text.

    Matches any retained term; ranks term coverage before frequency. This is keyword
    retrieval, not semantic understanding, Arabic stemming, or answer generation.
    An optional connection allows reuse by a future API or test.
    """
    terms = query_terms(question)
    if not terms:
        raise ValueError("Enter meaningful search words or numbers, not only question words.")
    if len(terms) > 64:
        raise ValueError("Use at most 64 distinct search terms.")
    if not domain.strip():
        raise ValueError("Domain must not be empty.")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    from psycopg.rows import dict_row

    def execute(conn):
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SEARCH_SQL, (terms, domain, limit))
            return list(cur.fetchall())

    if connection is not None:
        return execute(connection)
    from legal_rag.db import connect
    with connect() as conn:
        return execute(conn)


LOOKUP_SQL = """
SELECT u.unit_id, u.text, u.article_no, u.article_title,
       l.maqam_id, l.title AS document_title, l.number AS document_number,
       l.year AS document_year, u.verification, u.flags AS warnings,
       COALESCE(u.source_item_url, u.source_page_url, l.pdf_url) AS source_url
FROM units u JOIN legislation l ON l.maqam_id = u.maqam_id
WHERE l.maqam_id = %s AND u.article_no = %s
  AND l.domain = COALESCE(NULLIF(%s, 'all'), l.domain)
  AND u.kind = 'article' AND u.searchable
  AND l.superseded_by IS NULL
  AND l.jurisdiction IS DISTINCT FROM 'repealed'
"""


def lookup_article(document: int, article: int, domain: str = "labour", *, connection=None) -> list[dict]:
    """Look up an eligible full article by Maqam ID, NOT official law number.

    Reads original units directly, so no chunk splitting, ranking or keyword
    matching can omit part of the article. Returns [] for absent/excluded units.
    """
    if not isinstance(document, int) or isinstance(document, bool) or document <= 0:
        raise ValueError("Document must be a positive Maqam document ID.")
    if not isinstance(article, int) or isinstance(article, bool) or article <= 0:
        raise ValueError("Article number must be a positive integer.")
    if not domain.strip():
        raise ValueError("Domain must not be empty.")

    from psycopg.rows import dict_row

    def execute(conn):
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(LOOKUP_SQL, (document, article, domain))
            return list(cur.fetchall())

    if connection is not None:
        return execute(connection)
    from legal_rag.db import connect
    with connect() as conn:
        return execute(conn)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", help="Arabic keywords or a question (in quotes)")
    parser.add_argument("--document", type=int, help="Exact Maqam document ID (not official law number)")
    parser.add_argument("--article", type=int, help="Exact article number; requires --document")
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Save original results as UTF-8 JSON for reading in an editor")
    args = parser.parse_args()
    direct = args.document is not None or args.article is not None
    if direct and (args.document is None or args.article is None):
        parser.error("Provide both --document and --article.")
    if direct and args.question is not None:
        parser.error("Choose a question OR --document/--article, not both.")
    if not direct and args.question is None:
        parser.error("Provide a question or both --document and --article.")
    # UTF-8 preserves characters; Arabic shaping/direction depends on the terminal.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        results = (lookup_article(args.document, args.article, args.domain) if direct else
                   search(args.question, args.domain, args.limit))
    except ValueError as exc:
        parser.error(str(exc))
    except Exception as exc:
        # Do not echo connection strings or secrets from driver error details.
        from psycopg import Error
        if not isinstance(exc, (Error, RuntimeError)):
            raise
        raise SystemExit(
            f"Search failed ({type(exc).__name__}). Check PostgreSQL, .env, "
            "and that migrations and chunk generation have completed."
        ) from None
    if args.output:
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Saved {len(results)} results to {args.output}. Open the file in VS Code.")
        return
    if not results:
        print("No eligible article found for that document, article number and domain."
              if direct else "No keyword matches. Try fewer terms or wording from the legal text.")
        return
    for index, row in enumerate(results, start=1):
        print(f"\n--- Result {index} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
