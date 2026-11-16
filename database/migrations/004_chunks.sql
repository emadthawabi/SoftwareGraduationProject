-- Derived passages only. Original units are never modified.
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_kind TEXT NOT NULL CHECK (chunk_kind IN ('article', 'attachment', 'paragraph_group')),
    paragraph_labels TEXT[] NOT NULL DEFAULT '{}',
    content TEXT NOT NULL CHECK (length(content) > 0),
    context_header TEXT NOT NULL,
    embedding_input TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    chunker_version TEXT NOT NULL,
    warnings TEXT[] NOT NULL DEFAULT '{}',
    UNIQUE (unit_id, chunk_index)
);
CREATE INDEX chunks_input_hash_idx ON chunks(input_hash);
-- Embeddings are intentionally a later stage. Cache future vectors independently
-- by input_hash + model/settings so corpus reloads need not trigger paid calls.
