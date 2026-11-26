"""Adapt the initial companies scrape to loader schema without approving its text."""

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from legal_rag.load import (
    check_article_counts,
    check_refs_in,
    is_searchable,
    legislation_row,
    link_rows,
    read_jsonl,
    unit_row,
)


def adapt(legislation, units, snapshot_date=None):
    """Preserve source text and existing evidence. Missing verification stays untrusted."""
    legislation, units = copy.deepcopy(legislation), copy.deepcopy(units)
    lookup = {leg["maqam_id"]: leg for leg in legislation}
    if len(lookup) != len(legislation) or len({u["unit_id"] for u in units}) != len(units):
        raise ValueError("Duplicate document or unit IDs.")
    for leg in legislation:
        leg.setdefault("content_issue", "unreviewed_scrape; references and amendments not verified")
        # No saved raw HTML was supplied: do not invent its fingerprint/location.
        leg.setdefault("sha256", None)
        leg.setdefault("snapshot_date", snapshot_date)
        legislation_row(leg, "companies")
    for unit in units:
        leg = lookup[unit["legislation"]["maqam_id"]]
        if not unit["text"].strip():
            raise ValueError(f"Empty text: {unit['unit_id']}")
        expected = f"maqam:{leg['maqam_id']}:art:{unit['article_no']}"
        if unit["kind"] != "article" or unit["unit_id"] != expected:
            raise ValueError("Unexpected article identity.")
        url = unit.get("source_url") or leg.get("source_url")
        item = re.fullmatch(r"https://maqam\.najah\.edu/legislation/(\d+)/item/(\d+)/?", url or "")
        if item and int(item[1]) != leg["maqam_id"]:
            raise ValueError("Source item belongs to a different document.")
        defaults = {
            "lead_in": None, "paragraphs": [], "paragraph_kind": None,
            "text_source": leg.get("text_source", "html"), "verification": "unverified",
            "pdf_compared": False, "flags": [], "judgment_count": 0,
            "source_page_url": leg.get("source_url"),
            "source_item_url": url if item else None,
            "source_item_id": int(item[2]) if item else None,
            "raw_snapshot": None, "transcription": None,
            "sha256": hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
            "snapshot_date": snapshot_date, "refs_out": [], "refs_in": [],
            "delegated_from": [], "delegates_to": [],
        }
        for key, value in defaults.items():
            unit.setdefault(key, value)
        if unit["verification"] == "unverified":
            unit["needs_review"] = True
            unit["flags"] = list(dict.fromkeys([*unit["flags"], "unreviewed_scrape",
                                               "paragraphs_not_extracted", "references_not_extracted"]))
        unit_row(unit, is_searchable(unit, leg))
    check_article_counts(legislation, units)
    ids = {u["unit_id"] for u in units}
    check_refs_in(units, [r for u in units for r in link_rows(u, ids)])
    return legislation, units


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Save compatible corpus with original-file backups")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    corpus = root / "data/corpus/companies"
    summary_path = root / "data/parsed/legislation/1211/page_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    snapshot_date = datetime.fromisoformat(summary["retrieved_at"]).date().isoformat()
    originals = [read_jsonl(corpus / name) for name in ("legislation.jsonl", "units.jsonl")]
    legislation, units = adapt(*originals, snapshot_date)
    searchable = sum(is_searchable(u, next(l for l in legislation
                                         if l["maqam_id"] == u["legislation"]["maqam_id"])) for u in units)
    if args.write:
        for name, records in zip(("legislation.jsonl", "units.jsonl"), (legislation, units), strict=True):
            path = corpus / name
            backup = path.with_suffix(".before-schema.jsonl")
            if not backup.exists():
                backup.write_bytes(path.read_bytes())
            staging = path.with_suffix(".schema-tmp")
            staging.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
            staging.replace(path)
    print(f"{'Saved' if args.write else 'Preview'}: {len(legislation)} documents, {len(units)} units; {searchable} searchable.")
    print("Text is preserved. Schema compatibility does not establish source verification.")


if __name__ == "__main__":
    main()
