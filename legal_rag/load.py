"""Load a corpus folder (legislation.jsonl + units.jsonl) into the database.

The domain is the folder name (data/corpus/labour -> 'labour'). The load runs
in a single transaction: the domain's existing rows are deleted, everything is
inserted again, and the checks below must pass or nothing is committed.

Usage:
    python -m legal_rag.load data/corpus/labour --expect-searchable 405
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from psycopg.types.json import Jsonb

from legal_rag.db import connect

TRUSTED = {"verified_html", "verified_page_text", "pdf_transcribed_checked", "human_reviewed"}
SEARCHABLE_KINDS = {"article", "attachment"}

# refs_out kinds whose targets are paragraph labels inside the same المادة.
PARAGRAPH_KINDS = {"paragraph_internal"}


class LoadError(Exception):
    pass


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def article_unit_id(maqam_id: int, article_no: int) -> str:
    return f"maqam:{maqam_id}:art:{article_no}"


def is_searchable(unit: dict, leg: dict) -> bool:
    return (
        unit["kind"] in SEARCHABLE_KINDS
        and unit["verification"] in TRUSTED
        and leg["superseded_by"] is None
        and leg["jurisdiction"] != "repealed"
    )


# ---------------------------------------------------------------------------
# Row builders: JSON record -> tuple of column values
# ---------------------------------------------------------------------------

LEGISLATION_COLS = (
    "maqam_id", "domain", "title", "kind", "number", "year", "status", "status_source",
    "jurisdiction", "issued_under", "basis_articles", "superseded_by", "superseded_verified",
    "content_issue", "pdf_url", "article_count", "text_source", "sha256", "snapshot_date",
)


def legislation_row(leg: dict, domain: str) -> tuple:
    return (
        leg["maqam_id"], domain, leg["title"], leg["kind"], leg["number"], leg["year"],
        leg["status"], leg["status_source"], leg["jurisdiction"], leg["issued_under"],
        leg["basis_articles"] or [], leg["superseded_by"], leg["superseded_verified"],
        leg["content_issue"], leg["pdf_href"], leg["article_count"], leg["text_source"],
        leg["sha256"], leg["snapshot_date"],
    )


RELATION_COLS = (
    "from_maqam_id", "to_maqam_id", "relation", "derived_from", "evidence",
    "articles", "verified", "from_article",
)


def relation_rows(leg: dict) -> list[tuple]:
    return [
        (
            leg["maqam_id"], r["to"], r["relation"], r.get("derived_from"), r.get("evidence"),
            r.get("articles") or [], bool(r.get("verified")), r.get("from_article"),
        )
        for r in leg["relations"]
    ]


UNIT_COLS = (
    "unit_id", "maqam_id", "kind", "article_no", "article_title", "title_inferred", "part",
    "chapter", "position", "attachment_label", "after_article", "text", "lead_in",
    "paragraphs", "paragraph_kind", "text_source", "verification", "pdf_compared", "flags",
    "judgment_count", "source_page_url", "source_item_url", "source_item_id", "raw_snapshot",
    "transcription", "sha256", "snapshot_date", "searchable",
)


def unit_row(u: dict, searchable: bool) -> tuple:
    return (
        u["unit_id"], u["legislation"]["maqam_id"], u["kind"], u["article_no"],
        u["article_title"], bool(u["title_inferred"]), u["part"], u["chapter"], u["order"],
        u.get("attachment_label"), u.get("after_article"), u["text"], u["lead_in"],
        Jsonb(u["paragraphs"] or []), u["paragraph_kind"], u["text_source"], u["verification"],
        bool(u["pdf_compared"]), [flag_name(f) for f in u["flags"]], u["judgment_count"] or 0,
        u["source_page_url"], u["source_item_url"], u["source_item_id"], u["raw_snapshot"],
        u["transcription"], u["sha256"], u["snapshot_date"], searchable,
    )


def flag_name(flag) -> str:
    # Flags are plain strings; tolerate {"flag": ...} objects just in case.
    return flag if isinstance(flag, str) else flag.get("flag") or json.dumps(flag, ensure_ascii=False)


LINK_COLS = (
    "from_unit_id", "link_type", "to_unit_id", "to_maqam_id", "subtype", "raw", "resolved", "verified",
)


def link_rows(u: dict, unit_ids: set[str]) -> list[tuple]:
    """Turn refs_out / delegated_from / delegates_to into unit_links rows."""
    uid = u["unit_id"]
    own_maqam = u["legislation"]["maqam_id"]
    rows = []

    for r in u["refs_out"]:
        kind, raw, targets = r["kind"], r.get("raw"), r.get("targets") or []

        if kind in PARAGRAPH_KINDS:
            rows.append((uid, "reference", uid, None, kind, raw, True, None))
        elif not targets or r.get("resolved") is False:
            rows.append((uid, "reference", None, None, kind, raw, False, None))
        else:
            target_maqam = r.get("target_maqam_id") or own_maqam
            for n in targets:
                to = article_unit_id(target_maqam, n)
                if to not in unit_ids:
                    raise LoadError(f"{uid}: reference target {to} does not exist ({raw!r})")
                rows.append((uid, "reference", to, None, kind, raw, True, None))

    for d in u["delegated_from"]:
        to = article_unit_id(d["maqam_id"], d["article_no"])
        if to not in unit_ids:
            raise LoadError(f"{uid}: delegated_from target {to} does not exist")
        rows.append((uid, "implements", to, None, d["basis"], None, True, bool(d["verified"])))

    for d in u["delegates_to"]:
        rows.append((uid, "delegates_to", None, d["maqam_id"], d["basis"], None, True, bool(d["verified"])))

    return rows


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_refs_in(units: list[dict], links: list[tuple]) -> None:
    """Every refs_in entry must be the reverse of an inserted reference link (same التشريع)."""
    by_id = {u["unit_id"]: u for u in units}
    reversed_refs = Counter()
    for from_id, link_type, to_id, _, subtype, *_ in links:
        if link_type != "reference" or to_id is None or subtype in PARAGRAPH_KINDS:
            continue
        src, dst = by_id[from_id], by_id[to_id]
        if src["legislation"]["maqam_id"] == dst["legislation"]["maqam_id"]:
            reversed_refs[(to_id, src["article_no"], subtype)] += 1

    expected = Counter(
        (u["unit_id"], r["from"], r["kind"]) for u in units for r in u["refs_in"]
    )
    if reversed_refs != expected:
        missing = expected - reversed_refs
        extra = reversed_refs - expected
        raise LoadError(
            f"refs_in mismatch: {sum(missing.values())} in data but not derived "
            f"{list(missing)[:5]}, {sum(extra.values())} derived but not in data {list(extra)[:5]}"
        )


def check_article_counts(legislation: list[dict], units: list[dict]) -> None:
    counts = Counter(u["legislation"]["maqam_id"] for u in units if u["kind"] == "article")
    bad = [
        (leg["maqam_id"], leg["article_count"], counts[leg["maqam_id"]])
        for leg in legislation
        if leg["article_count"] is not None and leg["article_count"] != counts[leg["maqam_id"]]
    ]
    if bad:
        raise LoadError(f"article_count mismatch (maqam_id, expected, loaded): {bad}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def insert_many(cur, table: str, cols: tuple, rows: list[tuple]) -> None:
    if not rows:
        return
    placeholders = ", ".join(["%s"] * len(cols))
    cur.executemany(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})", rows)


def load(corpus_dir: Path, expect_searchable: int | None) -> dict:
    domain = corpus_dir.name
    legislation = read_jsonl(corpus_dir / "legislation.jsonl")
    units = read_jsonl(corpus_dir / "units.jsonl")

    leg_by_id = {leg["maqam_id"]: leg for leg in legislation}
    unit_ids = {u["unit_id"] for u in units}
    if len(leg_by_id) != len(legislation):
        raise LoadError("duplicate maqam_id in legislation.jsonl")
    if len(unit_ids) != len(units):
        raise LoadError("duplicate unit_id in units.jsonl")

    leg_rows = [legislation_row(leg, domain) for leg in legislation]
    rel_rows = [row for leg in legislation for row in relation_rows(leg)]
    u_rows, links = [], []
    for u in units:
        leg = leg_by_id.get(u["legislation"]["maqam_id"])
        if leg is None:
            raise LoadError(f"{u['unit_id']}: legislation {u['legislation']['maqam_id']} not in legislation.jsonl")
        u_rows.append(unit_row(u, is_searchable(u, leg)))
        links.extend(link_rows(u, unit_ids))

    searchable = sum(row[-1] for row in u_rows)
    if expect_searchable is not None and searchable != expect_searchable:
        raise LoadError(f"searchable units: expected {expect_searchable}, got {searchable}")
    check_article_counts(legislation, units)
    check_refs_in(units, links)

    with connect() as conn, conn.transaction(), conn.cursor() as cur:
        # ON DELETE CASCADE removes the domain's units, relations and links too.
        cur.execute("DELETE FROM legislation WHERE domain = %s", (domain,))
        insert_many(cur, "legislation", LEGISLATION_COLS, leg_rows)
        insert_many(cur, "legislation_relations", RELATION_COLS, rel_rows)
        insert_many(cur, "units", UNIT_COLS, u_rows)
        insert_many(cur, "unit_links", LINK_COLS, links)
        # Deferred foreign keys are checked here, before COMMIT.
        cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    return {
        "domain": domain,
        "legislation": len(leg_rows),
        "legislation_relations": len(rel_rows),
        "units": len(u_rows),
        "searchable": searchable,
        "unit_links": dict(Counter(row[1] for row in links)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("corpus_dir", type=Path, help="e.g. data/corpus/labour")
    parser.add_argument("--expect-searchable", type=int, help="fail unless exactly this many units are searchable")
    args = parser.parse_args()

    try:
        summary = load(args.corpus_dir, args.expect_searchable)
    except LoadError as e:
        raise SystemExit(f"Load failed, nothing was written: {e}")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
