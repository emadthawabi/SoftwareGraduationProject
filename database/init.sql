
CREATE EXTENSION IF NOT EXISTS vector;

-- Table 1: Laws, regulations and instructions
CREATE TABLE legal_documents (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    document_number VARCHAR(50),
    year INTEGER,
    category VARCHAR(100),
    source_url TEXT,
    legal_status VARCHAR(50) DEFAULT 'unverified'
);

-- Table 2: Individual legal articles
CREATE TABLE legal_articles (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL
        REFERENCES legal_documents(id)
        ON DELETE CASCADE,
    article_number VARCHAR(30) NOT NULL,
    chapter TEXT,
    article_text TEXT NOT NULL
);

-- Table 3: RAG chunks and embeddings
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    article_id BIGINT NOT NULL
        REFERENCES legal_articles(id)
        ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024),
    UNIQUE(article_id, chunk_index)
);

CREATE INDEX idx_chunks_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
