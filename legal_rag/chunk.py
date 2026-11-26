"""Prepare derived legal chunks. Preview reads corpus files; --write reads PostgreSQL."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from legal_rag.normalize import normalize_search_text

VERSION = "legal-boundaries-v2"
TRUSTED = {"verified_html", "verified_page_text", "pdf_transcribed_checked", "human_reviewed"}


def eligible(unit, legislation):
    return (unit["kind"] in {"article", "attachment"}
            and unit["verification"] in TRUSTED
            and legislation.get("superseded_by") is None
            and legislation.get("jurisdiction") != "repealed")


def header(unit, legislation, domain):
    fields = [("المجال", "العمل" if domain == "labour" else domain),
              ("التشريع", legislation["title"]), ("الباب", unit.get("part")),
              ("الفصل", unit.get("chapter")), ("المادة", unit.get("article_no")),
              ("عنوان المادة", unit.get("article_title")),
              ("الملحق", unit.get("attachment_label"))]
    return "\n".join(f"{label}: {value}" for label, value in fields if value is not None and value != "")


def segments(unit):
    """Locate top-level paragraph boundaries in ORIGINAL text; never reconstruct it.

    Everything between consecutive boundaries stays together, including nested
    items, punctuation and unparsed text. Fall back to the full unit if alignment
    is uncertain. Return prefix, contiguous spans, labels and a warning.
    """
    text = unit["text"]
    paragraphs = unit.get("paragraphs") or []
    if len(paragraphs) < 2:
        return "", [text], [], "no_safe_paragraph_boundaries"
    starts, labels, cursor = [], [], 0
    for paragraph in paragraphs:
        body = paragraph.get("text") or ""
        pos = text.find(body, cursor) if body else -1
        if pos < 0:
            return "", [text], [], "paragraph_alignment_failed"
        label = str(paragraph.get("label", ""))
        # Include the paragraph/definition label with its own content.
        line_start = text.rfind("\n", cursor, pos) + 1
        before = text[line_start:pos].strip()
        reverse_number = bool(label and re.fullmatch(r"\.\s*" + re.escape(label), before))
        if line_start >= cursor and (not before or reverse_number or
                (label and before.startswith(label) and
                 all(c in " .:-–—)٠١٢٣٤٥٦٧٨٩0123456789(\t" for c in before[len(label):]))):
            start = line_start
        else:
            # Some source pages flatten numbered paragraphs onto one line.
            marker = re.search(r"(?<!\w)" + re.escape(label) + r"\s*[.\-:،)–—]\s*$",
                               text[cursor:pos]) if label else None
            if marker:
                start = cursor + marker.start()
            elif not text[cursor:pos].strip(" \t\r\n.-:–—"):
                # A first marker can be missing in the source; keep its punctuation.
                start = cursor
            else:
                return "", [text], [], "paragraph_alignment_failed"
        starts.append(start)
        labels.append(label)
        cursor = pos + len(body)
    prefix = text[:starts[0]]
    spans = [text[start:end] for start, end in zip(starts, starts[1:] + [len(text)])]
    assert prefix + "".join(spans) == text
    return prefix, spans, labels, None


def split_long_span(text, limit):
    """Split at existing sentence/list boundaries only; retain every character.

    This is a continuation of one legal paragraph, not independent evidence.
    If no safe punctuation exists, retain the oversized span for review.
    """
    boundaries = [0] + [match.end() for match in re.finditer(
        r"(?:[.!؟؛;](?=\s)|\n)\s+", text)] + [len(text)]
    pieces, current = [], ""
    for start, end in zip(boundaries, boundaries[1:]):
        sentence = text[start:end]
        if current and len(current + sentence) > limit:
            pieces.append(current)
            current = ""
        current += sentence
    if current:
        pieces.append(current)
    return pieces


def nested_passages(span, outer_prefix, limit, level=0):
    """Split only at child-list boundaries; repeat governing introductions verbatim.

    Lettered children are split first, then their parenthesized numeric subitems.
    If an atomic item plus its context remains too long, leave it held for review.
    """
    if len(outer_prefix + span) <= limit:
        return [outer_prefix + span]
    patterns = [r"(?m)^[ \t]*[أابتثجحخدذرزسشصضطظعغفقكلمنهوي][.\-)]",
                r"(?m)^[ \t]*[0-9٠-٩]+\)"]
    if level >= len(patterns):
        return [outer_prefix + span]
    starts = [m.start() for m in re.finditer(patterns[level], span)]
    if not starts:
        return nested_passages(span, outer_prefix, limit, level + 1)
    intro = span[:starts[0]]
    context = outer_prefix + intro
    parts = [span[a:b] for a, b in zip(starts, starts[1:] + [len(span)])]
    assert intro + "".join(parts) == span
    result, current = [], ""
    for part in parts:
        if current and len(context + current + part) > limit:
            result.append(context + current)
            current = ""
        if len(context + part) > limit:
            result.extend(nested_passages(part, context, limit, level + 1))
        else:
            current += part
    if current:
        result.append(context + current)
    return result


def build_chunks(unit, legislation, domain, max_chars=1500):
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not eligible(unit, legislation):
        return []
    text = unit["text"]
    if not text.strip():
        raise ValueError(f"Empty searchable unit: {unit['unit_id']}")
    warnings = list(unit.get("flags") or [])
    if legislation.get("content_issue"):
        warnings.append("source_content_issue")
    groups = [(text, [], unit["kind"], False)]
    if unit["kind"] == "attachment":
        warnings.append("attachment_structure_review")
    elif len(text) > max_chars:
        prefix, spans, labels, warning = segments(unit)
        if warning:
            warnings.append(warning)
        else:
            groups, current, current_labels = [], "", []
            for span, label in zip(spans, labels):
                if len(prefix + span) > max_chars:
                    if current:
                        groups.append((prefix + current, current_labels, "paragraph_group", False))
                        current, current_labels = "", []
                    paragraph = (unit.get("paragraphs") or [])[labels.index(label)]
                    if domain == "companies" and paragraph.get("items"):
                        # Keep each child list under the complete parent introduction.
                        # These are contextual excerpts; retrieval returns full parent text.
                        for passage in nested_passages(span, prefix, max_chars):
                            groups.append((passage, [label], "paragraph_group", True))
                        continue
                    # Explicit nested structure wins over the size heuristic.
                    pieces = ([span] if paragraph.get("items") else
                              split_long_span(span, max(1, max_chars - len(prefix))))
                    groups.extend((prefix + piece, [label], "paragraph_group", len(pieces) > 1)
                                  for piece in pieces)
                    continue
                if current and len(prefix + current + span) > max_chars:
                    groups.append((prefix + current, current_labels, "paragraph_group", False))
                    current, current_labels = "", []
                current += span
                current_labels.append(label)
            if current:
                groups.append((prefix + current, current_labels, "paragraph_group", False))
    context = header(unit, legislation, domain)
    result = []
    for index, (content, labels, kind, continuation) in enumerate(groups):
        embedding_input = context + "\n\n" + content
        result.append({
            "chunk_id": f"{unit['unit_id']}:chunk:{index}",
            "unit_id": unit["unit_id"],
            "chunk_index": index,
            "chunk_kind": kind,
            "paragraph_labels": labels,
            "content": content,
            "context_header": context,
            "embedding_input": embedding_input,
            "search_text": normalize_search_text(embedding_input),
            "requires_parent_context": continuation,
            "embedding_ready": unit["kind"] != "attachment" and len(content) <= max_chars,
            "input_hash": hashlib.sha256(embedding_input.encode("utf-8")).hexdigest(),
            "chunker_version": f"{'companies-nested-v3' if domain == 'companies' else VERSION}:max_chars={max_chars}",
            "warnings": sorted(
                {str(w) for w in warnings}
                | ({"oversized_passage"} if len(content) > max_chars else set())
            ),
        })
    return result


def read_corpus(path):
    def records(name):
        with (path / name).open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
    legislation = records("legislation.jsonl")
    units = records("units.jsonl")
    by_id = {leg["maqam_id"]: leg for leg in legislation}
    if len(by_id) != len(legislation) or len({u["unit_id"] for u in units}) != len(units):
        raise ValueError("Duplicate legislation or unit IDs")
    return [(u, by_id[u["legislation"]["maqam_id"]]) for u in units]


def from_database(conn, domain):
    from psycopg.rows import dict_row
    with conn.cursor(row_factory=dict_row) as cur:
        # Lock the source domain against concurrent reloads while deriving chunks.
        cur.execute("""SELECT to_jsonb(u) AS unit, to_jsonb(l) AS legislation
                       FROM units u JOIN legislation l USING (maqam_id)
                       WHERE l.domain = %s ORDER BY u.unit_id FOR SHARE OF u, l""", (domain,))
        return [(row["unit"], row["legislation"]) for row in cur.fetchall()]


def prepare(pairs, domain, max_chars):
    return [chunk for unit, leg in sorted(pairs, key=lambda pair: pair[0]["unit_id"])
            for chunk in build_chunks(unit, leg, domain, max_chars)]


def write_chunks(conn, domain, chunks):
    columns = tuple(chunks[0])
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks c USING units u, legislation l "
                    "WHERE c.unit_id=u.unit_id AND u.maqam_id=l.maqam_id AND l.domain=%s", (domain,))
        cur.executemany(f"INSERT INTO chunks ({', '.join(columns)}) VALUES "
                        f"({', '.join(['%s'] * len(columns))})",
                        [tuple(chunk[column] for column in columns) for chunk in chunks])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="labour")
    parser.add_argument("--corpus-dir", type=Path, help="Preview input; default: data/corpus/<domain>")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="Read corpus only (default)")
    mode.add_argument("--write", action="store_true", help="Read database and replace this domain's chunks")
    parser.add_argument("--max-chars", type=int, default=1500)
    parser.add_argument("--samples", type=int, default=2)
    args = parser.parse_args()
    if args.max_chars <= 0 or args.samples < 0:
        parser.error("--max-chars must be positive; --samples must be nonnegative")
    if args.write and args.corpus_dir:
        parser.error("--corpus-dir is for preview only; --write uses database records")
    if args.write:
        from legal_rag.db import connect
        with connect() as conn, conn.transaction():
            pairs = from_database(conn, args.domain)
            chunks = prepare(pairs, args.domain, args.max_chars)
            if not chunks:
                raise SystemExit("No eligible units found; nothing changed. Load the domain first.")
            write_chunks(conn, args.domain, chunks)
    else:
        pairs = read_corpus(args.corpus_dir or Path("data/corpus") / args.domain)
        chunks = prepare(pairs, args.domain, args.max_chars)
    print(f"Mode: {'written to database' if args.write else 'preview (no database writes)'}")
    print(f"Source units: {len(pairs)}; eligible units: {len({c['unit_id'] for c in chunks})}; chunks: {len(chunks)}")
    print(f"Embedding-ready (token check still required): {sum(c['embedding_ready'] for c in chunks)}")
    print("Review before embedding:", [c["chunk_id"] for c in chunks if not c["embedding_ready"]])
    print("Warnings:", dict(Counter(w for c in chunks for w in c["warnings"])))
    for chunk in chunks[:args.samples]:
        print(json.dumps(chunk, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
