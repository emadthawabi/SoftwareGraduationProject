-- Run the chunk writer after this migration to populate normalized text.
ALTER TABLE chunks
    ADD COLUMN search_text TEXT NOT NULL DEFAULT '',
    ADD COLUMN requires_parent_context BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN embedding_ready BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN search_vector TSVECTOR GENERATED ALWAYS AS
        (to_tsvector('simple'::regconfig, search_text)) STORED;

CREATE INDEX chunks_search_vector_idx ON chunks USING GIN (search_vector);
-- 'simple' tokenization is deliberate: this is not an Arabic morphological stemmer.
-- Normalize user questions with legal_rag.normalize.normalize_search_text too.
