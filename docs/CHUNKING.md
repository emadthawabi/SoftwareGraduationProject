# Legal chunk preparation

`legal_rag/chunk.py` creates derived passages without modifying original units.
It makes no API calls and generates no embeddings. No new dependencies are needed.

## Commands (PowerShell, project root)

Preview the local corpus without connecting to PostgreSQL:

```powershell
python -m legal_rag.chunk --domain labour --preview --samples 2
```

Samples use JSON Unicode escapes so Windows terminals with legacy encodings work.
These are display escapes only; stored text is Arabic Unicode.

Apply the new table migration and generate chunks from the loaded database:

```powershell
docker compose up -d
python -m legal_rag.migrate
python -m legal_rag.chunk --domain labour --write --samples 0
```

The source domain must already be loaded. Preview uses corpus files; write mode
uses the database's own source records, so counts differ if those sources differ.
The write replaces only the selected domain's chunks in a transaction. Source
rows are locked while reading; exceptions roll back the chunk replacement.
An empty eligible domain is rejected without deleting existing chunks.

## Rules

- Eligibility is the same as `load.py`: trusted article/attachment, no recorded
  replacement, jurisdiction not `repealed`.
- Short articles remain exact. Default soft passage threshold: 1,500 characters.
  Configure with `--max-chars`; this is not a token limit and excludes the header.
- Long articles are grouped at existing top-level paragraph boundaries. Exact
  slices preserve all intervening nested items, labels and punctuation.
- The original prefix before the first paragraph repeats in each child chunk.
- Definitions keep their labels and explanation together.
- If exact boundary alignment is uncertain, keep the full unit and report it.
- Attachments remain whole and carry `attachment_structure_review`: the corpus
  has flattened tables whose rows cannot reliably be reconstructed automatically.
- A paragraph/attachment may exceed the threshold; `oversized_passage` marks it.
  Review these before embedding and enforce the selected model's token limit then.
- Oversized paragraphs without explicit nested items are subdivided at existing
  sentence/list punctuation, preserving exact text. These continuations have
  `requires_parent_context=true`: retrieval must fetch their parent unit (or the
  necessary complete paragraph), not use them as independent legal evidence.
  Explicit nested item structures remain intact even if oversized.
- `embedding_ready=false` holds attachments and oversized passages for review.
  This is a preparation gate, NOT a token-limit check or legal validation.
  The three flattened attachments cannot be repaired by inventing table rows.
  Reconstruct/verify them against source documents before approving their use.
- Source flags propagate. They are not a legal validation or new exclusion policy.
- Context headers include domain, document title, available part/chapter, article
  number/title or attachment label. No missing headings are invented.

## The chunks table

`chunk_id` identifies a unit's zero-based chunk index; `unit_id` points to the
original parent for full-article context and citations. `chunk_index` orders it.
`chunk_kind` is article, attachment or paragraph_group. `paragraph_labels` records
covered definitions/paragraphs. `content` holds the passage; `context_header`
identifies it; `embedding_input` joins both. `input_hash` is SHA-256 of that exact
input. `chunker_version` includes algorithm version and size setting. `warnings`
records source flags and preparation issues. Chunk IDs alone do not imply that
text has stayed unchanged: use input_hash for that purpose.

## Separate keyword text (migration 005)

`legal_rag/normalize.py` creates `search_text` from the context header and passage.
It standardizes Arabic presentation forms, alef variants, Arabic/Persian digits,
whitespace and case; removes Arabic diacritics, tatweel and invisible formatting.
It preserves negation, numbers, punctuation, ta marbuta and alef maqsura. This is
an intentionally lossy search copy, never quotation text or embedding input.
Use the same `normalize_search_text()` function on user queries.

Migration 005 adds search_text, requires_parent_context, embedding_ready and a
generated search_vector with a GIN index. The PostgreSQL `simple` configuration
is tokenization without Arabic stemming, synonyms or clitic segmentation.
It is a keyword baseline, not complete Arabic linguistic search.

Run migrations then regenerate chunks to populate normalized text. Existing
rows get empty search_text and embedding_ready=false until regenerated.

```sql
-- This example query is already normalized. Normalize dynamic queries in Python.
SELECT c.chunk_id, u.article_no, c.content
FROM chunks c JOIN units u ON u.unit_id = c.unit_id
JOIN legislation l ON l.maqam_id = u.maqam_id
WHERE l.domain = 'labour' AND u.searchable AND c.embedding_ready
  AND c.search_vector @@ plainto_tsquery('simple', 'الاجر')
ORDER BY ts_rank_cd(c.search_vector, plainto_tsquery('simple', 'الاجر')) DESC;
```

Local v2 preview: 430 chunks / 405 units; 427 pass the preparation gate.
Three attachments remain held: maqam:535:att:1, maqam:857:att:1, maqam:864:att:1.
Two of those attachments exceed the character threshold. Warnings are retained,
not suppressed. All 13 tests pass. Live migration/write were not executed.

The FK cascades: reloading a corpus removes its derived chunks. Rebuild them with
the write command. No vectors exist yet. Future paid embeddings should be cached
independently by exact input hash plus model/dimensions/settings, so rebuilding
chunks does not require paying to embed unchanged input again.

## Checks

```powershell
python -m unittest discover -s tests -v
```

Tests cover source preservation, repeated prefix, nested items, attachments,
exclusions, stable output and coverage of the local 405-unit corpus if available.
They do not validate legal correctness. Database application needs a live server.

In DBeaver after writing:

```sql
SELECT count(*) AS chunks, count(DISTINCT unit_id) AS represented_units FROM chunks;
SELECT chunk_id, paragraph_labels, embedding_input, warnings
FROM chunks ORDER BY unit_id, chunk_index;
```
