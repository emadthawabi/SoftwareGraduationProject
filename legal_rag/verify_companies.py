"""Compare company corpus to saved Maqam HTML; never rewrite extracted legal text."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from legal_rag.load import read_jsonl

METHOD = "maqam-dt-dd-comparison-v2"
SOURCE = "https://maqam.najah.edu/legislation/1211/"


def whitespace(text):
    """Ignore HTML spacing only; preserve all letters, numbers and punctuation."""
    return re.sub(r"\s+", " ", text or "").strip()


def source_articles(html):
    soup = BeautifulSoup(html, "html.parser")
    articles = {}
    part = chapter = None
    # Use structural dt/dd boundaries, independently of the original flat-line scraper.
    for tag in soup.find_all(["h5", "h6", "dt"]):
        if tag.name == "h5":
            part, chapter = tag.get_text(" ", strip=True), None
        elif tag.name == "h6":
            chapter = tag.get_text(" ", strip=True)
        else:
            anchor = tag.find("a", href=re.compile(r"^/legislation/1211/item/\d+/?$"))
            if anchor is None:
                continue
            numbers = re.findall(r"\d+", anchor.get_text())
            if len(numbers) != 1:
                raise ValueError("Ambiguous article heading.")
            number = int(numbers[0])
            body = tag.find_next_sibling()
            if body is None or body.name != "dd" or number in articles:
                raise ValueError("Missing/duplicate source article boundary.")
            # dd excludes following headings, court references and website footer.
            lines = [line.strip() for line in body.get_text("\n", strip=True).splitlines() if line.strip()]
            articles[number] = {"text": "\n".join(lines), "part": part, "chapter": chapter,
                                "source_url": urljoin(SOURCE, anchor["href"])}
    if set(articles) != set(range(1, 347)):
        raise ValueError("Saved source does not contain exactly articles 1-346.")
    # Reviewed source artifact: article 65 ends with a duplicate heading for 66.
    # The actual article 66 has its own dt/dd block and distinct title/body.
    # Remove ONLY this exact trailing marker; never strip legal cross-references.
    text, separator, last = articles[65]["text"].rpartition("\n")
    if separator and last == "المادة (66)":
        articles[65]["text"] = text
        articles[65]["source_artifact"] = "duplicate_next_article_heading_removed:المادة (66)"
    return articles


def compare(unit, source):
    issues = []
    text = source["text"]
    title = unit.get("article_title")
    if title:
        first, separator, remainder = text.partition("\n")
        if not separator or whitespace(first) != whitespace(title):
            issues.append("title_boundary_mismatch")
        else:
            text = remainder
    if whitespace(text) != whitespace(unit["text"]):
        issues.append("body_text_mismatch")
    for name in ("part", "chapter"):
        if whitespace(unit.get(name)) != whitespace(source[name]):
            issues.append(name + "_mismatch")
    if unit.get("source_item_url") != source["source_url"]:
        issues.append("source_url_mismatch")
    return issues


def write_jsonl(path, records):
    backup = path.with_suffix(".before-verification.jsonl")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    staging = path.with_suffix(".verification-tmp")
    staging.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    staging.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--write", action="store_true", help="Record passing source checks and retain mismatches on hold")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    snapshot = args.snapshot.resolve()
    relative = snapshot.relative_to(root).as_posix()
    # Date reflects the saved source folder, never a fabricated review timestamp.
    from datetime import date

    snapshot_date = date.fromisoformat(snapshot.parent.name).isoformat()
    html = snapshot.read_bytes()
    sources = source_articles(html)
    corpus = root / "data/corpus/companies"
    units = read_jsonl(corpus / "units.jsonl")
    legislation = read_jsonl(corpus / "legislation.jsonl")
    if {u["article_no"] for u in units} != set(sources) or len(units) != 346:
        raise ValueError("Corpus IDs/coverage differ from source.")
    rows = []
    for unit in units:
        source = sources[unit["article_no"]]
        issues = compare(unit, source)
        verdict = "held" if issues else "verified_html"
        rows.append({"unit_id": unit["unit_id"], "article_no": unit["article_no"],
                     "verdict": verdict, "issues": issues, "source_url": source["source_url"],
                     "stored_text_sha256": hashlib.sha256(unit["text"].encode("utf-8")).hexdigest(),
                     "source_article_sha256": hashlib.sha256(source["text"].encode("utf-8")).hexdigest(),
                     "source_artifact": source.get("source_artifact"),
                     "source_text": source["text"] if issues else None})
        if args.write:
            unit["verification"] = "unverified" if issues else "verified_html"
            unit["needs_review"] = bool(issues)
            unit["raw_snapshot"] = relative
            unit["snapshot_date"] = snapshot_date
            unit["flags"] = [f for f in unit["flags"] if f != "unreviewed_scrape"
                             and not f.startswith("source_review:")]
            unit["flags"].extend("source_review:" + issue for issue in issues)
            if source.get("source_artifact"):
                if "source_duplicate_heading_omitted" not in unit["flags"]:
                    unit["flags"].append("source_duplicate_heading_omitted")
            unit["verification_evidence"] = {"method": METHOD, "snapshot": relative,
                                              "source_artifact": source.get("source_artifact"),
                                              "scope": "HTML text/title/headings/URL fidelity; not legal currency or PDF comparison"}
    passed = sum(r["verdict"] == "verified_html" for r in rows)
    report = {"method": METHOD, "snapshot": relative,
              "snapshot_sha256": hashlib.sha256(html).hexdigest(), "snapshot_date": snapshot_date,
              "total": len(rows), "passed": passed, "held": len(rows) - passed,
              "applied": args.write,
              "scope": "Whitespace-insensitive source fidelity only. No PDF, amendment completeness, jurisdiction applicability or legal opinion verification.",
              "articles": rows}
    output = root / "data/verification/companies"
    output.mkdir(parents=True, exist_ok=True)
    (output / "source-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "review_sheet.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["unit_id", "article_no", "verdict", "issues", "source_url"])
        writer.writeheader()
        writer.writerows({k: (";".join(r[k]) if k == "issues" else r[k]) for k in writer.fieldnames} for r in rows)
    if args.write:
        for leg in legislation:
            leg["sha256"] = report["snapshot_sha256"]
            leg["snapshot_date"] = snapshot_date
            leg["content_issue"] = f"{len(rows) - passed} articles held after source comparison; references/paragraph structures and amendment completeness not reviewed"
        write_jsonl(corpus / "units.jsonl", units)
        write_jsonl(corpus / "legislation.jsonl", legislation)
    print(f"Checked {len(rows)} articles: {passed} passed; {len(rows) - passed} held. Applied: {args.write}.")
    print("Held article numbers:", [r["article_no"] for r in rows if r["issues"]])
    print("Reports:", output)


if __name__ == "__main__":
    main()
