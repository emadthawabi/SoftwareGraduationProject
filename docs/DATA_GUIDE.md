# Data guide

An explanation of the data in `data/corpus/` and how it is stored in the database. The data provider's specification is [data.md](../data.md); this guide adds translations, a worked example and the database mapping.

## What the data is

Labour Law No. 7 of 2000 (Maqam ID 1) and its 36 related instruments: **37 pieces of legislation, 444 units**. Source: Maqam (maqam.najah.edu) and the official gazette PDFs, snapshot of 2026-11-12.

Each piece of legislation is split into **units**. A unit is one المادة (article), one ديباجة (preamble) or one ملحق (annex). The unit is what we search, show and cite.

## Arabic legal terms

| Arabic | English | Notes |
|---|---|---|
| تشريع | Legislation | Any legal instrument |
| قانون | Law | Passed by the legislature. Here: the Labour Law (1) |
| نظام | Regulation | Issued by the Council of Ministers under a law (13) |
| لائحة | Bylaw | Detailed rules (6) |
| قرار | Decision / decree | e.g. minimum wage decisions (8) |
| تعليمات | Instructions | Ministerial, technical (9) |
| المادة / المواد | Article / articles | The unit we cite |
| الفقرة / البند | Paragraph / item | Numbered parts of an article |
| الباب / الفصل | Part / chapter | Sections of the law (main law only) |
| ديباجة | Preamble | "Having reviewed ... and based on article X ..." |
| ملحق | Annex | Tables and forms |
| ساري النفاذ | In force | |

## The input files

| File | Contents |
|---|---|
| `corpus/labour/legislation.jsonl` | One row per piece of legislation: metadata and relations to other legislation |
| `corpus/labour/units.jsonl` | One row per unit: original text, structure, trust level, links, sources |

Everything else in `data/` (`raw/`, `transcriptions/`, `parsed/`, `relations/`, `verification/`) is source or intermediate material and is not used as input.

## Worked example: overtime

**Law article `maqam:1:art:71`**: part five (work conditions) → chapter one (working hours) → article 71, "ساعات العمل الإضافية" (overtime hours).

- `text`: (1) overtime may be agreed up to 12 hours a week; (2) each overtime hour is paid at one and a half times the normal rate.
- `paragraphs`: the same text split into paragraphs 1 and 2, so we can cite "article 71, paragraph 2".
- `verification: verified_html`: trusted, included in search.
- `refs_in`: articles 80 and 131 point to it (131 is the penalty for violating this chapter).
- `delegates_to: 533`: the working hours regulation implements it (`title_match`, not verified).
- `judgment_count: 34`: cited in 34 court judgments.

**Instrument article `maqam:533:art:3`**: "overtime may not exceed twelve hours a week."

- No title, part or chapter, as for all instruments. Out of context it does not say which law it belongs to, which is why chunks get a context header.
- `delegated_from`: implements law articles 68, 70 and 71.

**Legislation `533`**: regulation (نظام) No. 166 of 2004, issued under the Labour Law, in force, not superseded.

A question such as "كم ساعة إضافية مسموح أشتغل بالأسبوع؟" ("how many overtime hours may I work per week?") should find 71 and 533/3, with the penalty article attached as supporting material.

## `superseded_by`

`superseded_by` means the text has been replaced by a newer one.

- **371**: Council of Ministers Decision No. 11 of 2012, minimum wage (old amounts).
- **1160**: Decision No. 4 of 2021, sets new amounts and repeals "anything that conflicts with it" (its article 3).
- So 371 (and 503) have `superseded_by: 1160`.

`superseded_verified: false` means the link was inferred from the text of 1160 and is not officially confirmed; Maqam still lists 371 as in force. These texts are kept in the database but excluded from search, so they can be shown as "may have been replaced".

## Trust levels (`verification`)

| Status | Count | Meaning | Searchable |
|---|---|---|---|
| `verified_html` | 141 | Main law from saved HTML, structural checks pass | yes |
| `verified_page_text` | 254 | Copied from Maqam pages, numbering complete | yes |
| `pdf_transcribed_checked` | 18 | Typed from gazette PDF, numbers checked | yes |
| `pdf_transcribed_unchecked` | 25 | Typed from scanned PDFs, awaiting review | no |
| `human_reviewed` | 0 | Confirmed by a reviewer | yes |
| `flagged` | 6 | Known problem | no |

A unit is **searchable** when its kind is article or attachment, its status is trusted, its legislation is not superseded and not repealed: **405 units**. The 39 others are 25 unchecked transcriptions, 6 flagged units, 6 articles of the superseded decisions 371 and 503, and 2 trusted preambles.

## Database tables

The loader ([legal_rag/load.py](../legal_rag/load.py)) maps the two files to four tables.

```
legislation ──< legislation_relations >── legislation
     │
     └──< units ──< unit_links >── units / legislation
```

### `legislation` (from `legislation.jsonl`)

| Column | Source field | Meaning |
|---|---|---|
| `maqam_id` (PK) | `maqam_id` | Maqam ID of the legislation |
| `domain` | folder name | `labour`; lets new laws be added and filtered |
| `title`, `kind`, `number`, `year` | same | Title, type (قانون / نظام / ...), number, year |
| `status`, `status_source` | same | Status text from Maqam and where it came from |
| `jurisdiction` | same | `west_bank_and_gaza` or `unknown` |
| `issued_under` | same | Parent law (1 for every instrument) |
| `basis_articles` | same | Law articles named in the preamble |
| `superseded_by`, `superseded_verified` | same | Replaced by which legislation, and whether confirmed |
| `content_issue` | same | Known content problem (only 863) |
| `pdf_url` | `pdf_href` | Official gazette PDF |
| `article_count`, `text_source` | same | Number of articles; where the text came from |
| `sha256`, `snapshot_date` | same | Content fingerprint and snapshot date |

### `legislation_relations` (from `relations` in `legislation.jsonl`)

| Column | Meaning |
|---|---|
| `from_maqam_id`, `to_maqam_id` | Source and target. The target is empty for legislation outside the corpus |
| `relation` | `issued_under`, `related`, `based_on`, `superseded_by`, `repeals`, `mentions` |
| `derived_from` | How it was found: `maqam_list`, `preamble`, `article_text`, `content` |
| `evidence` | Supporting text |
| `articles`, `from_article` | Articles involved; the article whose text states the relation |
| `verified` | Confirmed or not |

### `units` (from `units.jsonl`)

| Column | Source field | Meaning |
|---|---|---|
| `unit_id` (PK) | same | `maqam:<id>:art:<n>`, `maqam:<id>:preamble`, `maqam:<id>:att:<k>` |
| `maqam_id` | `legislation.maqam_id` | Which legislation it belongs to |
| `kind` | same | `article`, `preamble`, `attachment` |
| `article_no`, `article_title`, `title_inferred` | same | Number, title (main law only), whether the title was inferred |
| `part`, `chapter` | same | الباب, الفصل (main law only) |
| `position` | `order` | Order within the legislation (renamed: `ORDER` is reserved in SQL; empty for preambles and most annexes) |
| `attachment_label`, `after_article` | same | Annexes only |
| `text` | same | **Original wording, never modified** |
| `lead_in`, `paragraphs`, `paragraph_kind` | same | Introductory sentence, paragraphs (JSON), `numbered` or `definitions` |
| `text_source`, `verification`, `pdf_compared`, `flags` | same | Origin, trust level, PDF comparison, parsing notes |
| `judgment_count` | same | Court judgments citing the article |
| `source_page_url`, `source_item_url`, `source_item_id` | same | Maqam links for citations |
| `raw_snapshot`, `transcription`, `sha256`, `snapshot_date` | same | Audit trail |
| `searchable` | computed | Included in search (rule above) |

The copied `legislation` object is not stored (it is reached through `maqam_id`). `refs_in`, `refs_out`, `delegates_to` and `delegated_from` become rows in `unit_links`.

### `unit_links` (from `refs_out`, `delegated_from`, `delegates_to`)

| `link_type` | Meaning | Example |
|---|---|---|
| `reference` | The unit's text refers to another unit; one row per target | 131 → 68 ... 80 |
| `implements` | An instrument article implements a law article | 533/3 → 1/71 |
| `delegates_to` | A law article is implemented by a whole piece of legislation | 1/71 → legislation 533 |

| Column | Meaning |
|---|---|
| `from_unit_id` | Source unit |
| `to_unit_id` / `to_maqam_id` | Target unit, or target legislation for `delegates_to` |
| `subtype` | For references: `article`, `self_part`, `chapter_of_part`, `law_article`, `paragraph_internal`, `external_law`, ... For delegation: `explicit`, `title_match`, `preamble` |
| `raw` | Original phrase, e.g. "هذا الفصل" |
| `resolved` | False for targets outside the corpus ("قانون النقابات", the schedule in article 128) |
| `verified` | For delegation links |

`refs_in` is not stored: it is the reverse of `reference` rows and is derived by query. The loader checks that the reverse matches `refs_in` exactly.

## Known issues

- **863 (الإضاءة):** Maqam shows the noise instructions' text under this title; all its units are flagged.
- **Missing tables:** 860, 861 and 537 refer to "الجدول المرفق" (the attached table), which is absent.
- **Minimum wage:** the supersession of 371 and 503 by 1160 is unverified.
- **Main law:** the "الباب الثاني" heading appears twice (articles 7–23 are flagged `duplicate_part_number`); parts 6–9 have no chapters.
- **Lost markers:** some articles start with ". " because the "1" was lost; `paragraphs` labels it `1` with the flag `leading_marker_missing_in_source`.
- **Coarse delegation links:** `title_match` links all articles of an instrument to a law article, even definitions.
- **Keyword search alone misses matches:** "الحد الأدنى للأجور" (minimum wage) does not appear in the wording of article 89.
