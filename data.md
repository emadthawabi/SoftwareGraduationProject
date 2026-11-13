# DATA.md — what is in `data/` and how to read it

Companion to `AGENTS.md`. Everything here is **read-only** for the RAG phase: report problems, never edit these files.

## 1. What the data is

قانون العمل الفلسطيني رقم (7) لسنة 2000 (Maqam ID 1) plus its **36 related instruments** (أنظمة، لوائح، قرارات، تعليمات) — **37 التشريعات, 444 units**. Source: Maqam (maqam.najah.edu) and the official gazette PDFs, snapshot 2026-11-12.

## 2. Folders

| Path | Use in the RAG phase |
|---|---|
| `corpus/labour/units.jsonl` | **The input.** One unit per line (المادة, ديباجة, or ملحق) |
| `corpus/labour/legislation.jsonl` | One row per التشريع: metadata + relations between التشريعات |
| `verification/review_sheet.csv` | 59 units awaiting human verdicts (read-only for you) |
| `relations/` | Reference/delegation files — already merged into `units.jsonl`; ignore |
| `raw/`, `transcriptions/`, `parsed/` | Original sources and intermediate files — do not use as input |

## 3. A unit (`units.jsonl`)

Real example (shortened):

```json
{
  "unit_id": "maqam:1:art:89",
  "kind": "article",
  "legislation": {"maqam_id": 1, "title": "قانون العمل الفلسطيني رقم (7) لسنة 2000م",
                  "kind": "قانون", "number": 7, "year": 2000,
                  "status": "ساري النفاذ في الضفة الغربية وغزة",
                  "jurisdiction": "west_bank_and_gaza", "superseded_by": null},
  "article_no": 89,
  "article_title": "الحد الأدنى للأجور",
  "part": "الباب الخامس شروط وظروف العمل",
  "chapter": "الفصل الثالث الأجور",
  "text": "لا يجوز أن يقل أجر العامل عن الحد الأدنى المقر قانوناً.",
  "paragraphs": [],
  "verification": "verified_html",
  "refs_in": [{"from": 132, "kind": "chapter_of_part"}],
  "delegates_to": [{"maqam_id": 1160, "basis": "title_match", "verified": false}],
  "judgment_count": 4,
  "source_item_url": "https://maqam.najah.edu/legislation/1/item/89/"
}
```

| Field | Meaning |
|---|---|
| `unit_id` | Stable ID — use it everywhere (chunks, citations, the app). `maqam:<id>:art:<n>`, `maqam:<id>:preamble`, `maqam:<id>:att:<k>` |
| `kind` | `article` 432 · `preamble` 6 · `attachment` 6 |
| `legislation` | Copy of the التشريع's metadata (no join needed) |
| `article_no` / `article_title` | المادة number / title (titles exist only in the main law) |
| `part` / `chapter` | الباب / الفصل — main law only, `null` elsewhere |
| `text` | **Original wording. Never change it.** Normalize only in separate search copies |
| `lead_in`, `paragraphs`, `paragraph_kind` | المادة split into الفقرات/البنود (`numbered`) or terms (`definitions`). 156 units have them; nested items are under `items` |
| `text_source` | `html` (main law) · `page_text` (copied from Maqam pages) · `pdf_transcription` |
| `verification` | Trust level — see section 5 |
| `refs_out` / `refs_in` | Links to/from other units. `targets` are المادة numbers; `target_maqam_id: 1` means "in the law", otherwise "in the same التشريع" |
| `delegates_to` | On law المواد: which instruments implement it |
| `delegated_from` | On instrument units: which law المادة it implements |
| `judgment_count` | Court judgments citing the المادة on Maqam — a signal of practical importance |
| `flags` | Notes from parsing (section 6) |
| `source_page_url`, `source_item_url` | Links for citations |

Instrument units look the same but with `part`/`chapter`/`article_title` = `null` and `delegated_from` filled, e.g. `maqam:533:art:3` (نظام ساعات العمل): "لا يجوز أن تزيد ساعات العمل الإضافي على اثنتي عشرة ساعة في الأسبوع." → `delegated_from` law المواد 68–71.

## 4. A التشريع (`legislation.jsonl`)

Key fields: `maqam_id`, `title`, `kind`, `number`, `year`, `status`, `jurisdiction`, `issued_under` (1 for all instruments), `basis_articles` (law المواد named in the instrument's ديباجة), `superseded_by` + `superseded_verified`, `article_count`, `content_issue`, and `relations` — a list of `{to, relation, derived_from, evidence, verified}` where `relation` ∈ `related`, `issued_under`, `based_on`, `superseded_by`, `repeals`, `mentions`.

## 5. Trust: `verification`

| Status | Count | Meaning | Search by default? |
|---|---|---|---|
| `verified_html` | 141 | Main law from saved HTML, all structural checks pass | yes |
| `verified_page_text` | 254 | Copied from Maqam pages, numbering complete | yes |
| `pdf_transcribed_checked` | 18 | Typed from gazette PDF; all numbers match the PDF text layer | yes |
| `pdf_transcribed_unchecked` | 25 | Typed from scanned PDFs (862, 1128, 1133, 1134); awaiting review | no |
| `human_reviewed` | 0 | Confirmed by a reviewer (appears after verdicts) | yes |
| `flagged` | 6 | Known problem (863 wrong text; 1133 annex with unreadable values) | no |

**Default searchable set:** trusted statuses above, `kind` ∈ {article, attachment}, `superseded_by` is null, `jurisdiction` ≠ repealed → **405 units**.

## 6. Known issues to keep in mind

- **863 (الإضاءة):** Maqam shows the noise instructions' text under this title → all units flagged.
- **Missing tables:** 860, 861, 537 refer to "الجدول المرفق" but the table is absent (`table_missing_in_source`).
- **Minimum wage:** 371 and 503 (2012) marked `superseded_by: 1160` (2021) — **unverified**; Maqam still lists them as in force.
- **Main law quirks:** "الباب الثاني" heading appears twice (المواد 7–23 flagged `duplicate_part_number`); الأبواب 6–9 have no الفصول.
- **Lost markers:** some المواد start with ". " in the source (the "1" was lost); `paragraphs` labels it `1` with the flag `leading_marker_missing_in_source`; `text` is unchanged.
- **Annexes** (857 model penalty list, 864 heat tables, 535 forms, 1133 criteria, 1134 contract models) are separate `attachment` units.

## 7. Useful facts for design

- Size: 432 المواد; text length median ~164 characters, 90th percentile ~550, max ~7,900 (11 المواد over 1,500).
- References inside the law are already resolved (e.g. 131 → 68–80; 134 → 93–106; 136 → 116, 117).
- Law → instrument links come from the instruments' own ديباجة (verified, e.g. 21 → 1134, 15 → 1128, 9 → 1133, 139 → 1129) or from title matching (unverified).
- Keyword search alone misses some obvious matches: "الحد الأدنى للأجور" does not match المادة 89's wording.