# Progress

Last updated: 2026-11-23

## Stages

| # | Stage | Status |
|---|---|---|
| 1 | Gold question set (questions with known correct المواد) | ⏳ Not started |
| 2 | Database schema + loading the data | ✅ Done |
| 3 | Arabic normalization + chunking | Implemented; 3 flattened attachments require source review |
| 4 | Indexes: Postgres full-text (Arabic) + pgvector embeddings | ⬜ |
| 5 | Retrieval: direct lookup → query rewriting → hybrid search (RRF) → rerank → link expansion | ⬜ |
| 6 | Answer generation with citations | ⬜ |
| 7 | Evaluation, one component at a time | ⬜ |
| — | Phase 2: retrieval from real case descriptions | ⬜ |

## Done

### Semantic query test (2026-11-23)

- Added `legal_rag.semantic_search`: converts original questions with Gemini
  RETRIEVAL_QUERY into normalized 1536-dimensional vectors and saves UTF-8 JSON.
- Read-only cosine retrieval filters the complete document embedding profile and
  returns distinct units with the best passage, full parent text and source URL.
- Live Arabic weekly-hours query saved question-vector-test.json with its actual
  1536 numbers and five passages. Database currently links 427 eligible chunks.
- Similarity is a ranking score, not a probability or legal correctness guarantee.

### Resumable Gemini embedding generation (2026-11-23)

- Added `python -m legal_rag.embed`: preview by default; `--write` generates vectors.
- Filters eligible chunks, verifies exact input hashes and fresh Gemini token counts,
  reuses full-profile cached embeddings, normalizes 1536-dimensional outputs and
  commits each validated batch separately. Bounded retries handle transient HTTP errors.
- Live test: `--limit 5 --write` saved five vectors; verified dimensions, unit length
  and five current chunk links. Repeating reused all five without API calls.
- Three held attachments stay excluded. Full-corpus embedding has not been run.
- Added six offline safety tests; usage is in docs/EMBEDDING_STORAGE.md.

### Embedding storage (2026-11-23)

- Added migration 006: embedding_cache holds 1536-dimensional L2-normalized vectors
  keyed by exact input hash plus provider/model/task/configuration identity.
- chunk_embeddings view attaches current eligible chunks to matching cached vectors.
  Cache entries survive source reloads; stale hashes do not match changed chunks.
- No generation script, embedding API requests or production migration execution
  are included in this step. See docs/EMBEDDING_STORAGE.md for application commands.
- PostgreSQL integration test passed in an isolated rolled-back schema: dimensions,
  normalization, uniqueness, stale hashes, review gates and rebuild reuse checked.

### Gemini token validation (2026-11-23)

- Added gemini-embedding-001 support using the provider's actual countTokens API,
  never an OpenAI tokenizer estimate. Added google-genai to requirements and
  non-secret Gemini settings to .env.example.
- Reads EMBEDDING_MODEL from .env or accepts explicit --model. Uses 2040 safe input
  tokens under the 2048 maximum, reserving 8 for framing/internal overhead.
- Holds and input-hash checks remain; identical text reuses counts within a run.
- All 33 tests passed, including mocked Gemini request shape and safe boundaries.
- Full live validation uses read-only database access; no embeddings are generated.
- Live Gemini validation: 430 chunks checked, 427 pass, 3 held. Largest candidate
  621 tokens, candidate total 68975. One held attachment (maqam:535:att:1) is 3221
  tokens and exceeds the safe limit. Saved token-report-gemini.json separately.

### Token preflight (2026-11-18)

- Added read-only `legal_rag/validate_tokens.py` and tiktoken dependency.
- Counts exact embedding_input including headings using the selected model's
  tokenizer, checks input fingerprints and keeps preparation holds separate.
- Corpus validation with text-embedding-3-small: 430 chunks, 427 can pass preflight,
  3 held attachments, 0 oversized/empty inputs, 0 hash mismatches. Largest prepared
  candidate: 1169 tokens; candidates total: 133139 tokens. No embeddings generated.
- Tokenizer vocabulary downloaded once; legal text was processed locally.
- Read-only database validation matched corpus results. All 30 tests passed.

### Direct article lookup (2026-11-18)

- `search.py` now accepts `--document <Maqam ID> --article <number>` instead of a
  question. Parameterized lookup returns the full eligible article and sources
  directly from units, independent of chunks and keyword ranking.
- Missing, non-searchable, superseded or recorded-repealed articles are excluded.
- Existing keyword mode and UTF-8 JSON output remain available; no migration.
- All 24 tests passed. Live read-only checks confirmed 1/71 and 534/1 return
  their exact units and 1/99999 returns no result.

### Keyword retrieval (2026-11-18)

- Added `legal_rag/search.py`: normalized, parameterized PostgreSQL keyword search,
  deterministic ranking and one result per legal unit (default top five).
- Results include the matched chunk, full parent article, citation metadata and
  source warnings. Review-held attachments are excluded.
- Uses existing migrations; no new database structure or model calls required.
- Query terms now use partial OR matching after conservative question-word removal;
  distinct term coverage ranks before frequency. Negation and numbers remain in
  the query but OR retrieval does not enforce them as logical constraints.
- All 16 tests passed. A read-only live database search for ساعات العمل الإضافية
  returned maqam:1:art:71 as the top result. No database writes were performed.

### Chunk refinement and keyword text (2026-11-16)

- v2 splits oversized unstructured article paragraphs at existing sentence/list
  boundaries; marks continuations as requiring parent context at retrieval time.
- Added conservative Arabic normalization, separate search_text and migration 005
  for a generated PostgreSQL simple-config search_vector plus GIN index.
- Local preview: 430 chunks covering 405 units, 427 preparation-ready; 3 flattened
  attachments remain held for source review, including 2 oversized attachments.
- All 13 tests pass, including corpus preservation and normalization checks.
- No live migrations, database writes, model API calls or embeddings executed.
- Token counting and embedding generation remain pending. Keyword normalization
  must also be applied to future search queries; no Arabic stemming is implied.

### Chunk preparation (2026-11-16)

- Added `legal_rag/chunk.py`, migration `004_chunks.sql`, and source-preservation tests.
- Preview reads the local corpus; write mode derives chunks from PostgreSQL.
- Short articles stay whole; long articles use source paragraph boundaries and
  repeated introductory context. Attachments remain whole with review warnings.
- Original text and corpus files are unchanged. Embeddings are not generated.
- See `docs/CHUNKING.md` for commands, reload behavior and limitations.
- Migration and live database write have not been applied by the coding agent.
- Local preview: 444 source units, 405 eligible units, 423 chunks; 4 oversized
  passages and 3 attachments marked for structure review. All 8 tests passed.

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
