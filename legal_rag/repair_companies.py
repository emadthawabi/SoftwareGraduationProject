"""Repair reviewed company extraction boundaries/headings from the saved HTML."""

import argparse
import hashlib
import json
from pathlib import Path

from legal_rag.load import read_jsonl
from legal_rag.verify_companies import compare, source_articles


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    corpus = root / "data/corpus/companies/units.jsonl"
    snapshot = root / "data/raw/maqam/legislation/1211/2026-11-25/verification-page.html"
    sources = source_articles(snapshot.read_bytes())
    units = read_jsonl(corpus)
    changes = []
    for unit in units:
        source = sources[unit["article_no"]]
        issues = compare(unit, source)
        if not issues:
            continue
        before = {key: unit.get(key) for key in ("text", "article_title", "part", "chapter", "sha256")}
        if "body_text_mismatch" in issues or "title_boundary_mismatch" in issues:
            title, separator, text = source["text"].partition("\n")
            if not separator:
                raise ValueError("Missing title boundary; manual review required.")
            if unit["article_no"] not in {66, 226, 346}:
                raise ValueError("Unexpected text change; manual review required.")
            unit["article_title"] = title
            unit["text"] = text
        unit["part"] = source["part"] or None
        unit["chapter"] = source["chapter"] or None
        unit["sha256"] = hashlib.sha256(unit["text"].encode("utf-8")).hexdigest()
        if compare(unit, source):
            raise ValueError("Repaired record does not match source.")
        changes.append({"unit_id": unit["unit_id"], "issues_resolved": issues, "before": before,
                        "after": {key: unit.get(key) for key in before}})
    if args.write:
        backup = corpus.with_suffix(".before-source-repair.jsonl")
        if not backup.exists():
            backup.write_bytes(corpus.read_bytes())
        audit = root / "data/verification/companies/extraction-repairs.json"
        if changes:
            audit.write_text(json.dumps({"snapshot": str(snapshot.relative_to(root)),
                                         "changes": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging = corpus.with_suffix(".repair-tmp")
        staging.write_text("".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units), encoding="utf-8")
        staging.replace(corpus)
    print(f"{'Repaired' if args.write else 'Would repair'} {len(changes)} records. Run verify_companies --write afterward.")


if __name__ == "__main__":
    main()
