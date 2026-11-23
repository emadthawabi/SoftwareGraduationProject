-- Cached vectors have NO foreign key to chunks: source reloads must not delete
-- expensive reusable embeddings. Link to current chunks by exact input_hash.
-- This first storage format is deliberately fixed at 1536 dimensions.
CREATE TABLE embedding_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider TEXT NOT NULL CHECK (length(btrim(provider)) > 0),
    model TEXT NOT NULL CHECK (length(btrim(model)) > 0),
    dimensions INTEGER NOT NULL DEFAULT 1536 CHECK (dimensions = 1536),
    task_type TEXT NOT NULL DEFAULT 'RETRIEVAL_DOCUMENT'
        CHECK (task_type = 'RETRIEVAL_DOCUMENT'),
    normalization TEXT NOT NULL DEFAULT 'l2' CHECK (normalization = 'l2'),
    -- Increment if request options, title handling, or model revision changes.
    -- v1: input=exact embedding_input, no separate title, output=1536, L2 normalized.
    request_version TEXT NOT NULL DEFAULT 'gemini-retrieval-v1'
        CHECK (length(btrim(request_version)) > 0),
    input_hash TEXT NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    token_count INTEGER NOT NULL CHECK (token_count > 0),
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Negative inner product with itself is -1 for an L2-normalized vector.
    CHECK (abs((embedding <#> embedding) + 1) < 0.001),
    UNIQUE (provider, model, dimensions, task_type, normalization,
            request_version, input_hash)
);

CREATE INDEX embedding_cache_input_hash_idx ON embedding_cache(input_hash);

-- A view, not another stored copy. Changed hashes stop matching automatically;
-- cached vectors survive reloads and reattach when the same inputs are rebuilt.
CREATE VIEW chunk_embeddings AS
SELECT c.chunk_id, c.unit_id, l.domain, e.id AS embedding_id,
       e.provider, e.model, e.dimensions, e.task_type, e.normalization,
       e.request_version, e.input_hash, e.token_count, e.embedding, e.created_at
FROM chunks c
JOIN units u ON u.unit_id = c.unit_id
JOIN legislation l ON l.maqam_id = u.maqam_id
JOIN embedding_cache e ON e.input_hash = c.input_hash
WHERE c.embedding_ready AND u.searchable
  AND l.superseded_by IS NULL
  AND l.jurisdiction IS DISTINCT FROM 'repealed';

-- Small initial corpus: exact cosine search is sufficient. No approximate vector
-- index is required yet. Future retrieval MUST filter the complete model/profile
-- (provider, model, dimensions, task_type, normalization and request_version).
