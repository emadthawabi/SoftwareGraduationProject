-- 001_schema.sql — source-of-truth tables for legislation and its units.
-- Search tables (chunks, embeddings) come in a later migration.

CREATE EXTENSION IF NOT EXISTS vector;

-- Tables from the first prototype schema (replaced by this one).
DROP TABLE IF EXISTS document_chunks, legal_articles, legal_documents CASCADE;


-- ---------------------------------------------------------------------------
-- legislation: one row per التشريع (law, نظام, لائحة, قرار, تعليمات)
-- ---------------------------------------------------------------------------
CREATE TABLE legislation (
    maqam_id            INTEGER PRIMARY KEY,
    domain              TEXT    NOT NULL,              -- e.g. 'labour'
    title               TEXT    NOT NULL,
    kind                TEXT    NOT NULL,              -- قانون / نظام / لائحة / قرار / تعليمات
    number              INTEGER,
    year                INTEGER,
    status              TEXT,                          -- raw status text from Maqam
    status_source       TEXT,
    jurisdiction        TEXT,                          -- west_bank_and_gaza / unknown / ...
    -- Self-references are DEFERRABLE so a whole corpus can be loaded in one
    -- transaction without caring about row order.
    issued_under        INTEGER REFERENCES legislation (maqam_id)
                            DEFERRABLE INITIALLY DEFERRED,
    basis_articles      INTEGER[] NOT NULL DEFAULT '{}',
    superseded_by       INTEGER REFERENCES legislation (maqam_id)
                            DEFERRABLE INITIALLY DEFERRED,
    superseded_verified BOOLEAN,
    content_issue       TEXT,
    pdf_url             TEXT,
    article_count       INTEGER,
    text_source         TEXT,
    sha256              TEXT,
    snapshot_date       DATE
);

CREATE INDEX legislation_domain_idx ON legislation (domain);


-- ---------------------------------------------------------------------------
-- legislation_relations: links between التشريعات
-- ---------------------------------------------------------------------------
CREATE TABLE legislation_relations (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_maqam_id  INTEGER NOT NULL REFERENCES legislation (maqam_id)
                       ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    to_maqam_id    INTEGER NOT NULL REFERENCES legislation (maqam_id)
                       ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    relation       TEXT    NOT NULL,   -- issued_under / related / based_on / superseded_by / repeals / mentions
    derived_from   TEXT,               -- maqam_list / preamble / article_text / content
    evidence       TEXT,
    articles       INTEGER[] NOT NULL DEFAULT '{}',
    verified       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX legislation_relations_from_idx ON legislation_relations (from_maqam_id);
CREATE INDEX legislation_relations_to_idx   ON legislation_relations (to_maqam_id);


-- ---------------------------------------------------------------------------
-- units: one row per المادة / ديباجة / ملحق — the original, unmodified text
-- ---------------------------------------------------------------------------
CREATE TABLE units (
    unit_id          TEXT    PRIMARY KEY,             -- maqam:<id>:art:<n> | :preamble | :att:<k>
    maqam_id         INTEGER NOT NULL REFERENCES legislation (maqam_id)
                         ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    kind             TEXT    NOT NULL CHECK (kind IN ('article', 'preamble', 'attachment')),
    article_no       INTEGER,
    article_title    TEXT,
    title_inferred   BOOLEAN NOT NULL DEFAULT FALSE,
    part             TEXT,                            -- الباب
    chapter          TEXT,                            -- الفصل
    position         INTEGER NOT NULL,                -- "order" in the source (reserved word in SQL)
    attachment_label TEXT,
    after_article    INTEGER,
    text             TEXT    NOT NULL,                -- original wording, never modified
    lead_in          TEXT,
    paragraphs       JSONB   NOT NULL DEFAULT '[]',
    paragraph_kind   TEXT,                            -- numbered / definitions
    text_source      TEXT,                            -- html / page_text / pdf_transcription
    verification     TEXT    NOT NULL,
    pdf_compared     BOOLEAN NOT NULL DEFAULT FALSE,
    flags            TEXT[]  NOT NULL DEFAULT '{}',
    judgment_count   INTEGER NOT NULL DEFAULT 0,
    source_page_url  TEXT,
    source_item_url  TEXT,
    source_item_id   INTEGER,
    raw_snapshot     TEXT,
    transcription    TEXT,
    sha256           TEXT,
    snapshot_date    DATE,
    searchable       BOOLEAN NOT NULL,                -- computed by the loader (DATA.md §5)

    CHECK (kind <> 'article' OR article_no IS NOT NULL)
);

CREATE INDEX units_maqam_idx      ON units (maqam_id);
CREATE INDEX units_searchable_idx ON units (searchable);
-- Direct lookup: "المادة 47" of a given التشريع.
CREATE UNIQUE INDEX units_article_no_uq ON units (maqam_id, article_no) WHERE kind = 'article';


-- ---------------------------------------------------------------------------
-- unit_links: the graph between units
--   reference    : from_unit's text refers to to_unit       (refs_out, one row per target)
--   implements   : instrument unit implements a law المادة  (delegated_from)
--   delegates_to : law المادة is implemented by a whole التشريع (delegates_to)
-- ---------------------------------------------------------------------------
CREATE TABLE unit_links (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_unit_id  TEXT    NOT NULL REFERENCES units (unit_id)
                      ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    link_type     TEXT    NOT NULL CHECK (link_type IN ('reference', 'implements', 'delegates_to')),
    to_unit_id    TEXT    REFERENCES units (unit_id)
                      ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    to_maqam_id   INTEGER REFERENCES legislation (maqam_id)
                      ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    subtype       TEXT    NOT NULL,   -- reference: article, self_part, ... | implements/delegates_to: explicit, title_match, preamble
    raw           TEXT,               -- original phrase, e.g. 'هذا الفصل'
    resolved      BOOLEAN NOT NULL DEFAULT TRUE,
    verified      BOOLEAN,

    CHECK (to_unit_id IS NOT NULL OR to_maqam_id IS NOT NULL OR NOT resolved)
);

CREATE INDEX unit_links_from_idx ON unit_links (from_unit_id);
CREATE INDEX unit_links_to_idx   ON unit_links (to_unit_id);
CREATE INDEX unit_links_to_leg_idx ON unit_links (to_maqam_id);
