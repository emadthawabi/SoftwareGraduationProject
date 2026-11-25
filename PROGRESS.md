# Progress

Last updated: 2026-11-25

## Current state (read before historical entries)

- Implemented: corpus loading, Arabic normalized keyword text, chunk preparation,
  token validation, cached Gemini embeddings, semantic + keyword RRF retrieval,
  Gemini Arabic answers with citations, clarification prompts and bounded retries.
- Labour snapshot last verified: 427 eligible chunks linked to vectors; three
  attachments remain held. Future legal fields STILL require their own ingestion,
  chunking, token validation, embeddings and evaluation. See docs/NEW_DOMAINS.md.
- Models: gemini-embedding-001 (1536 dimensions) and generation default
  gemini-3.5-flash-lite; one GEMINI_API_KEY. Groq/OpenAI entries below are history.
- Last full suite: 55 passed, one optional DB test skipped. Current answer prompt v3.
- Known open issue: test-v10.json confidently answers lateness-warning criteria with
  general disciplinary rules. Review held attachment maqam:857:att:1 for the schedule;
  do not claim the specific rule has already been retrieved or verified.
- No chat memory/API integration, automatic domain routing, reranker, query rewriting
  or link expansion yet. A formal repeatable evaluation dataset is still pending.
- HANDOFF.md summarizes decisions and next work. Older entries describe what was
  true at that step and may mention superseded providers or incomplete embeddings.

## Stages

| # | Stage | Status |
|---|---|---|
| 1 | Gold question set (questions with known correct المواد) | ⏳ Not started |
| 2 | Database schema + loading the data | ✅ Done |
| 3 | Arabic normalization + chunking | Implemented; 3 flattened attachments require source review |
| 4 | Indexes: Postgres full-text (Arabic) + pgvector embeddings | Implemented for labour; held attachments/new domains pending |
| 5 | Retrieval: direct lookup → query rewriting → hybrid search (RRF) → rerank → link expansion | Direct lookup + hybrid done; rewrite/rerank/expansion pending |
| 6 | Answer generation with citations | Implemented; reliability/coverage evaluation continues |
| 7 | Evaluation, one component at a time | Automated tests + manual examples; formal dataset pending |
| — | Phase 2: retrieval from real case descriptions | ⬜ |

## Done

### Selective clarification for calculations (2026-11-25)

- Prompt arabic-evidence-v4 distinguishes complete arithmetic inputs from ambiguous
  legal classification, missing inputs and unsupported deduction requests.
- Instructs direct calculation using supplied facts, without invented registration
  conditions, redundant wage confirmation or assuming basic wage is the calculation base.
- Added Arabic wording guidance; old saved outputs are retained as baselines.

### Ambiguous employment and retirement questions (2026-11-24)

- Updated prompt to arabic-evidence-v3: do not equate profit sharing with commission
  employment or assume employee/partner status. Ask for the arrangement and apply
  category-specific rules conditionally while applicability is unknown.
- Distinguish end-of-service compensation from pension rights; explicitly identify
  evidence gaps and ask what the user means by retirement. No embedding/DB changes.

### Temporary answer-generation failures (2026-11-24)

- Added at most three generation retries for HTTP 500/502/503/504 with exponential
  delays and jitter. The same model request and retrieved sources are reused;
  question embedding and retrieval do not repeat. Other errors fail immediately.
- SDK retries remain disabled to avoid multiplying attempts. Exhaustion preserves
  the existing error behavior and does not fabricate an answer.

### Answer wording and missing-fact handling (2026-11-24)

- Updated the generation instructions to correct false assumptions directly, preserve
  unknown eligibility conditions, request specific missing personal facts, show
  calculations and distinguish missing source evidence from missing user details.
- Added prompt_version=arabic-evidence-v2 to outputs for comparison with older runs.
- No schema migration or document re-embedding is required. Prompt instructions do
  not guarantee factual correctness; citation checks still only verify membership.
- Six existing answer tests passed. Live comparison saved a clearer direct correction
  in answer-false-assumption-improved.json. Missing-fact generation hit provider 503;
  colloquial output still omitted clarification, prompting a more explicit example.

### Gemini answer-generation switch (2026-11-24)

- Replaced Groq with the installed Google GenAI SDK. Both question embedding and
  answer generation use GEMINI_API_KEY; GROQ_API_KEY is no longer read.
- Answers default to gemini-3.5-flash-lite, configurable through ANSWER_MODEL.
  Existing embeddings, hybrid retrieval and local citation checks are unchanged.
- Added JSON-schema response configuration and incomplete/blocked response checks;
  updated answer tests and setup documentation.
- Verification: 53 tests passed, one optional integration test skipped. Live
  end-to-end maternity query succeeded and saved answer-maternity.json using Gemini.

### Arabic answer generation (2026-11-24)

- Added `legal_rag.answer`: hybrid retrieval followed by Groq-hosted
  openai/gpt-oss-120b with strict JSON output and Arabic evidence-only instructions.
- Cited claims carry verified source IDs; source links come from retrieval metadata.
  Empty context abstains locally; partial and insufficient responses are supported.
- Checks citation membership, response structure and completion status. These checks
  do not establish factual entailment; out-of-domain behavior needs live evaluation.
- Added GROQ_API_KEY placeholder to .env.example and docs/ANSWER_GENERATION.md.
- Live generation is pending: GROQ_API_KEY is not configured in the local environment.

### Hybrid retrieval (2026-11-24)

- Added `legal_rag.hybrid_search`, combining existing keyword and semantic
  retrieval using equal-weight RRF: sum(1 / (60 + rank)). Default: 20 candidates
  per method, five final distinct source units, deterministic ties by unit_id.
- Keeps each method's rank, original score and matched excerpt, plus full parent
  text and source URL. Raw keyword/similarity scores are not mixed together.
- Each request embeds the question once. Existing document embeddings are reused;
  database schema and stored data do not change. No answering model is called.
- Verification: 47 tests passed, one optional integration test skipped. Live
  hybrid check could not finish because PostgreSQL connection timed out.
- Run: `python -m legal_rag.hybrid_search "ما حقوق العاملة عند الولادة؟" --output hybrid-results.json`

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
