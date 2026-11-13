# Progress

Last updated: 2026-11-13

## Stages

| # | Stage | Status |
|---|---|---|
| 1 | Gold question set (questions with known correct المواد) | ⏳ Not started |
| 2 | Database schema + loading the data | ✅ Done |
| 3 | Arabic normalization + chunking | ⬜ Next |
| 4 | Indexes: Postgres full-text (Arabic) + pgvector embeddings | ⬜ |
| 5 | Retrieval: direct lookup → query rewriting → hybrid search (RRF) → rerank → link expansion | ⬜ |
| 6 | Answer generation with citations | ⬜ |
| 7 | Evaluation, one component at a time | ⬜ |
| — | Phase 2: retrieval from real case descriptions | ⬜ |

## Done

### Stage 2: database (2026-11-13)

- PostgreSQL 16 + pgvector in Docker ([docker-compose.yml](docker-compose.yml)).
- Migrations in [database/migrations/](database/migrations/), applied by [legal_rag/migrate.py](legal_rag/migrate.py):
  - `001_schema.sql`: tables `legislation`, `legislation_relations`, `units`, `unit_links`.
  - `002_relations_external_targets.sql`: relations may point to legislation outside the corpus (e.g. المادة 140 repeals the 1960 and 1964 labour laws).
  - `003_units_position_nullable.sql`: preambles and most annexes have no order in the source.
- Loader [legal_rag/load.py](legal_rag/load.py): one transaction per domain, idempotent, checks before committing.
- Loaded and verified for the labour domain:

| | Count |
|---|---|
| legislation | 37 |
| legislation_relations | 79 |
| units | 444 (405 searchable) |
| unit_links | 586 (181 reference, 361 implements, 44 delegates_to) |

Verified: text and paragraphs identical to the source for all 444 units; the 39 non-searchable units match data.md; `refs_in` equals the reverse of the loaded references; per-legislation article counts match; reloading gives identical counts.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Database | PostgreSQL + pgvector, one system | Relational data with links, Arabic full-text search and vector search in one place; scales well beyond this corpus |
| Store originals before indexing | Yes | Indexes are derived and rebuildable; citations and filters come from the database |
| Primary keys | `maqam_id`, `unit_id` from the data | Stable across reloads |
| Searchable set | article/attachment, trusted verification, not superseded, not repealed (405) | Rules from data.md §5 |
| Superseded texts (371, 503 → 1160) | Kept, excluded from search | Supersession is unverified; they can be shown as "may have been replaced" |
| Reloading | Full delete and reinsert per domain | 444 rows load in under a second; `sha256` will be used to avoid re-embedding unchanged text |
| Migrations | Plain numbered SQL files + small runner | Simple to understand; enough for this project |
| LLM / embeddings | OpenAI API | Chosen by the team |
| Chunking (planned) | One المادة per chunk with a context header; long المواد split into child chunks per الفقرة that return the full parent | Median article is ~164 characters; citations stay clean |
| Link expansion (planned) | Rerank first, then attach linked units as supporting results | Keeps linked units from crowding out direct matches |

## Open questions

- **Reranker:** add a Cohere key for `rerank-v3.5`, or use OpenAI only (an LLM as reranker)? Needed by stage 5.
- **Who asks the questions:** lawyers (formal wording) or the public (colloquial)? Affects how much query rewriting matters.
- **Gold set reviewer:** someone with legal knowledge to approve the questions and answers.

## Known issues to handle later

- `title_match` delegation links are coarse: all 7 articles of 533 are linked to law المادة 71, including definitions. Link expansion should prefer `explicit` and `preamble` links.
- 863 (الإضاءة) shows the wrong text on Maqam; all its units are flagged.
- 860, 861 and 537 refer to a table that is missing from the source.
- The supersession of 371 and 503 by 1160 is unverified.
