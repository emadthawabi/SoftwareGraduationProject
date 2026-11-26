"""Extract conservative paragraph metadata from original company-law text."""

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from legal_rag.chunk import segments
from legal_rag.load import read_jsonl

# Source uses both 1. and .1. Parenthesized numeric lists remain inside parents.
NUMBER = re.compile(
    r"(?m)^[ \t]*(?:(?P<duplicate>\d+)\s+\.(?P=duplicate)|"
    r"(?P<normal>\d+)[.\-]|[.](?P<reverse>\d+)|(?P<bare>\d+)(?=[ \t]+\S))[ \t]*")
DEFINITION = re.compile(r"(?m)^([^\W\d_][^:\n]{0,99}):[ \t]*", re.UNICODE)
NESTED = re.compile(r"(?m)^[ \t]*(?:([أابتثجحخدذرزسشصضطظعغفقكلمنهوي])[.\-)]|([0-9٠-٩]+)\))[ \t]*")
VERSION = "companies-paragraphs-v2"


def slice_paragraphs(text, matches, labels):
    paragraphs = []
    for index, (match, label) in enumerate(zip(matches, labels, strict=True)):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        if not body:
            raise ValueError("Empty paragraph body.")
        paragraph = {"label": label, "text": body}
        children = list(NESTED.finditer(body))
        if children:
            paragraph["items"] = [
                {"label": m[1] or m[2],
                 "text": body[m.end():children[i + 1].start() if i + 1 < len(children) else len(body)].strip()}
                for i, m in enumerate(children)
            ]
        paragraphs.append(paragraph)
    return paragraphs


def extract(unit):
    """Add derived structure only. Never repair numbering or change source text."""
    result = copy.deepcopy(unit)
    text = unit["text"]
    result.update(paragraphs=[], paragraph_kind=None, lead_in=None)
    result["flags"] = [f for f in unit.get("flags", [])
                       if f not in {"paragraphs_not_extracted", "paragraph_structure_review"}]
    matches = list(NUMBER.finditer(text))
    reason = None
    if matches:
        labels = [next(m[name] for name in ("duplicate", "normal", "reverse", "bare") if m[name])
                  for m in matches]
        numbers = [int(label) for label in labels]
        if numbers != list(range(1, len(numbers) + 1)):
            reason = "nonconsecutive_numbering"
        else:
            result["paragraphs"] = slice_paragraphs(text, matches, labels)
            result["paragraph_kind"] = "numbered"
    elif unit.get("article_title") == "تعاريف":
        # Intro itself may span lines and end in a colon. It is not a definition.
        colon = text.find(":")
        matches = [m for m in DEFINITION.finditer(text) if colon >= 0 and m.start() > colon]
        labels = [m[1] for m in matches]
        if len(matches) < 2 or len(set(labels)) != len(labels):
            reason = "ambiguous_definitions"
        else:
            result["paragraphs"] = slice_paragraphs(text, matches, labels)
            result["paragraph_kind"] = "definitions"
    elif NESTED.search(text):
        reason = "letter_or_nested_only_list"
    if result["paragraphs"]:
        result["lead_in"] = text[:matches[0].start()].strip() or None
        if len(result["paragraphs"]) > 1:
            prefix, spans, _, warning = segments(result)
            if warning or prefix + "".join(spans) != text:
                reason = "chunker_alignment_failed"
        if reason:
            result.update(paragraphs=[], paragraph_kind=None, lead_in=None)
    if reason:
        result["flags"].append("paragraph_structure_review")
    result["paragraph_extraction"] = {"version": VERSION, "review_reason": reason}
    assert result["text"] == unit["text"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = root / "data/corpus/companies/units.jsonl"
    originals = read_jsonl(path)
    units = [extract(u) for u in originals]
    report = {"version": VERSION, "total": len(units), "applied": args.write,
              "kinds": dict(Counter(u["paragraph_kind"] or "unstructured" for u in units)),
              "paragraph_count": sum(len(u["paragraphs"]) for u in units),
              "review": [{"unit_id": u["unit_id"], "reason": u["paragraph_extraction"]["review_reason"]}
                         for u in units if u["paragraph_extraction"]["review_reason"]]}
    if args.write:
        for old, new in zip(originals, units, strict=True):
            assert old["text"] == new["text"] and old["sha256"] == new["sha256"]
            assert hashlib.sha256(new["text"].encode("utf-8")).hexdigest() == new["sha256"]
        backup = path.with_suffix(".before-paragraphs.jsonl")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        staging = path.with_suffix(".paragraphs-tmp")
        staging.write_text("".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units), encoding="utf-8")
        staging.replace(path)
        (root / "data/verification/companies/paragraph-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
