# Embedding storage (migration 006)

## Generate embeddings

The generator is `legal_rag/embed.py`. It uses Gemini's hosted API; no model is
installed locally. Keep GEMINI_API_KEY, EMBEDDING_MODEL=gemini-embedding-001 and
EMBEDDING_DIMENSIONS=1536 in the existing .env. Never commit the key.

Preview without API calls or writes:

```powershell
python -m legal_rag.embed --limit 5
```

Generate only the first five eligible chunks:

```powershell
python -m legal_rag.embed --limit 5 --write
```

The limit selects the same source rows on each run, before checking the cache.
Repeating this command reuses those five vectors instead of embedding five more.
Once that test succeeds, process the remaining eligible inputs:

```powershell
python -m legal_rag.embed --write
```

Each uncached input is checked with Gemini countTokens before embedding; inputs
above 2040 tokens are rejected, never deliberately truncated. Original Arabic
embedding_input is sent unchanged with RETRIEVAL_DOCUMENT task type. Responses
must contain one finite, nonzero 1536-dimensional vector per input; vectors are
L2-normalized before storage. Reported provider truncation is also rejected.

Default batch size is five. Each complete valid batch commits separately. Rerun
after failure or Ctrl+C to reuse saved vectors. Transient HTTP 429/5xx errors
receive up to three retries with bounded backoff; persistent quota failures stop
the command. An API request that succeeded before a network/database failure may
need repeating if its vectors were not saved. Avoid concurrent generator runs
to avoid duplicate API requests, even though the database prevents duplicate rows.

Cache matching uses the full model/profile identity plus the exact input hash.
Three preparation-held attachments remain excluded. No sources are edited.

On 2026-11-23 the five-input live test saved five vectors. All had 1536 dimensions
and approximately unit length, and linked to five eligible chunks. Repeating the
same command made no Gemini calls and inserted no new vectors.

Apply from the project root:

```powershell
python -m legal_rag.migrate
```

This creates storage only: no API requests or embeddings are generated.

## embedding_cache table

| Column | Purpose |
|---|---|
| id | Generated identifier for a cached vector. |
| provider | Provider identity; use google for current Gemini integration. |
| model | Exact requested model name: gemini-embedding-001. |
| dimensions | 1536; constrained to match vector storage. |
| task_type | RETRIEVAL_DOCUMENT; query vectors are not persisted here. |
| normalization | l2; generator must normalize before insertion. |
| request_version | gemini-retrieval-v1: exact input, no separate title, 1536 dimensions, L2 normalization. |
| input_hash | SHA-256 of exact embedding_input, including headings. |
| token_count | Positive provider token count, including framing if counted. |
| embedding | Non-null pgvector VECTOR(1536), approximately unit length. |
| created_at | Insertion timestamp. |

The composite unique key includes provider, model, dimensions, task_type,
normalization, request_version and input_hash. Another configuration is a separate
cache entry, even when input text is identical. Future code must bump request_version
when changing options not represented by other columns, including separate titles
or a provider model revision. Fixed dimensions do not mean the table supports every
future model: another size needs a deliberate schema migration.

## chunk_embeddings view

This appears under Views in DBeaver. It connects chunks to vectors using input_hash
and retains only eligible, preparation-ready source units. It includes chunk_id,
unit_id, domain, embedding_id and all vector/profile metadata. Multiple profiles
can match the same chunk; future retrieval must filter the complete desired profile.
The view does not independently verify that a stored hash matches source text;
the generator must recompute hashes before saving. The source-review gate remains.

Cached vectors have no FK to chunks. Deleting/reloading a domain removes its chunks
but preserves the cache. Rebuilding identical chunks restores view matches without
new API calls. Changed hashes do not match old vectors. Retained unused cache rows
consume storage and may eventually need an explicit cleanup policy.

For the small corpus, exact cosine search can use pgvector without an approximate
index. No HNSW index is created at this stage.

Check after migration:

```sql
SELECT count(*) FROM embedding_cache;
SELECT count(*) FROM chunk_embeddings;
```

Both are initially zero. The existing chunks and original source tables remain.

## Verification

Opt-in integration test uses an isolated schema inside a rolled-back transaction:

```powershell
$env:LEGAL_RAG_TEST_DATABASE = '1'
python -m unittest discover -s tests -p test_embedding_storage.py -v
Remove-Item Env:LEGAL_RAG_TEST_DATABASE
```

Checks schema execution, vector size/unit length, unique profile keys, stale-hash
isolation, review holds and reuse after chunk rebuild. No real source rows change.
