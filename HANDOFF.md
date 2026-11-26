# Agent handoff — current state

Updated: 2026-11-26. This is a working summary, not the full chat transcript.
Read AGENTS.md and verify the repository/database before making changes.

## Project and team

Palestinian legal RAG graduation project with Arabic questions and cited answers.
The user handles AI/RAG; their partner handles the website. Mobile/Flutter is
postponed. The user wants small, clearly explained steps. More legal fields will
be supplied later; do not treat corpus preparation or embeddings as globally done.

## Implemented pipeline

AUDIT 2026-11-26: semantic_search.py was restored to an older single-domain filter;
fixed again to support all and return source domains. Added real-vector DB regression.
All 77 tests pass with DB integration enabled. Dependencies/imports and migrations
check out. DB text equals local corpora, all 427 labour + 385 companies ready chunks
have current-profile vector links, zero chunk hash mismatches. No new embeddings or
source/DB mutations in this audit. Historical lower test totals below are superseded.

LATEST routing: answer and hybrid commands now default to domain=all (all loaded
fields); explicit domain flags retain restricted search. Keyword/vector queries
honor all with full eligibility/profile filters. Source metadata includes domain.
Simple bare article-text requests use DB matching: ambiguous numbers ask which law,
unique eligible matches return original text without Gemini. Parser is intentionally
limited; complex natural document references and paragraph requests are not routed
deterministically yet. Full offline suite: 75 passed, one optional DB test skipped.

Source corpus -> PostgreSQL -> derived chunks and normalized keyword text ->
Gemini document vectors -> keyword + semantic retrieval -> equal-weight RRF ->
Gemini Arabic answer with citations or partial/insufficient evidence status.

- Database: PostgreSQL 16 + pgvector in Docker; see docker-compose.yml and db.py.
- Migrations: 001 through 006; never rewrite applied migrations.
- Embedding: gemini-embedding-001, 1536 dimensions, L2 normalized.
- Document/query tasks: RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY respectively.
- Persistent document cache: embedding_cache; current eligible links in
  chunk_embeddings view. Cache survives reloads and reuses identical input hashes
  only under the matching provider/model/task/dimension/normalization/request profile.
- Keyword matching normalizes Arabic but has no stemming or synonym expansion.
- hybrid_search.py uses 20 candidates/method and up to five final distinct units
  by default, RRF k=60. It retains full parent text and each method's excerpt/rank.
- answer.py uses GEMINI_API_KEY; generation default gemini-3.5-flash-lite, override
  ANSWER_MODEL. Inspect .env.example, not secret values. Groq is no longer used.
- Current prompt version arabic-evidence-v4: direct corrections, selective clarification,
  conditional category application, pension/end-of-service distinction. Complete
  calculation inputs should not trigger invented worker-registration requirements.
- JSON schema + local checks reject malformed answers, unknown citation IDs and
  incomplete responses. They do not verify claim entailment or legal currency.
- Generation retries HTTP 500/502/503/504 up to three times after increasing delays
  plus jitter, reusing context. Other errors stop. Repeated 503s occurred in testing.
- No conversation memory, API/chat endpoint, calibrated relevance gate, reranker,
  automatic domain routing or reference-link expansion has been implemented here.

## Corpus and remaining preparation

LATEST companies DB check: all 385 eligible company chunks are linked to current
cached embeddings. Token report supplied by user: all 385 pass, max 596 tokens,
110340 total tokens. Earlier pending-load/embedding statements below are historical.
LLC registration test exposed RRF overlap bias: article 65 semantic #1/keyword #40
was omitted. Hybrid now reserves a slot for semantic #1 when limit>1 if RRF would
discard it; ranks/scores unchanged. Do not mistake this for relevance calibration.
Latest suite: 71 passed, one optional DB test skipped.

LATEST: seven company oversized holds resolved in corpus preview. Paragraph v2 now
recognizes source bare/duplicated numeric labels without text edits: 264 numbered
articles + one definitions article, 973 entries, 81 plain articles. Chunker applies
company-specific nested excerpts with full governing introductions repeated and
requires_parent_context=true. Preview 385 chunks, all preparation-ready; token
validation still pending. No DB changes in this review step: user must reload
companies (--expect-searchable 346) and regenerate its chunks to replace prior 376.
Labour nested chunking unchanged. Latest suite 69 passed, one optional DB test skipped.
Historical counts below refer to earlier snapshots.

Latest paragraph preparation: legal_rag.paragraphs --write added 927 top-level
entries across 256 numbered articles plus article 1 definitions. 81 articles remain
plain text, eight have ambiguous/nonconsecutive numbering (169,178,185,202,231,245,
290,326) and are flagged paragraph_structure_review without invented clauses.
Text, hashes and verification preserved; backup units.before-paragraphs.jsonl and
report data/verification/companies/paragraph-report.json. Nested lists stay with
their numeric parent. Chunker supports source .1/.2 markers without changing text.
Companies corpus chunk preview: 376 chunks, 369 preparation-ready, seven oversized
holds (178,200,245,29,290,48,87). Token checks/DB chunk writes/embeddings still pending.
Latest full suite: 65 passed, one optional DB test skipped. No DB writes in this step.

Latest companies update: reviewed repairs now applied; all 346 pass HTML comparison
v2 and are verified_html, 0 held. Corrected headings in 16 records and title/body
boundaries in 66,226,346, with before/after audit extraction-repairs.json and backup.
Article 65 legal text unchanged: explicit reviewed trailing marker exception in
verify_companies, also visible in the individual Maqam item page. No DB load or
company embeddings yet. Next load with --expect-searchable 346, then chunk/token
review and embeddings. Older review counts below describe the earlier snapshot.

Companies domain now supplied: data/corpus/companies, Maqam 1211, one document,
346 articles (1-346). Schema adapted by legal_rag.prepare_companies with original
corpus backups. All source comparisons now complete: 326 verified_html, 20 held.
Evidence is saved under data/raw/maqam/legislation/1211/2026-11-25/; per-article
reports are under data/verification/companies/. verify_companies uses independent
dt/dd blocks, title/body, heading state and article URLs; only whitespace is ignored.
Text was preserved. Held articles: 65,66,226,227,228,321-326,338-346. Fix extraction
only through an explicitly reviewed change; snapshots show footer/boundary/heading
issues. No companies DB load or embeddings yet. Paragraph/reference extraction,
PDF comparison and amendment completeness still pending. Latest suite: 60 passed,
one optional DB test skipped. Do not treat HTML checks as verification of currency.

Last verified labour snapshot: 37 documents, 444 source units, 405 searchable units,
430 derived chunks, 427 embedding-eligible chunks linked to stored vectors.
These are historical verified counts, not a substitute for checking the current DB.
Three attachments remain held from retrieval/embedding:

- maqam:535:att:1:chunk:0
- maqam:857:att:1:chunk:0
- maqam:864:att:1:chunk:0

They need original-source structure review; do not remove holds just to increase
coverage. Existing source text must not be silently edited.

Other fields are planned. Their corpus files, trust checks, chunks, normalized
search copies and vectors STILL need processing when supplied. See
docs/NEW_DOMAINS.md. Current CLI retrieval defaults to labour; pass --domain to
search another field. There is no automatic all-fields search.

General pension legislation is absent from the current labour corpus. Maqam has
قانون التقاعد العام رقم (7) لسنة 2005م at https://maqam.najah.edu/legislation/102/,
but scope/amendments require review before future ingestion. Do not equate a pension
with end-of-service compensation or assume profit sharing means commission employment.

## Last unresolved test

test-v10.json asks when a late-arriving employee may receive a warning. It returns
general article 3 of Maqam document 857 and labels the answer answered. Those
passages do not establish the specific lateness thresholds/conditions, so the answer
is incomplete and should be partial. Inspect the held penalties attachment 857
against its source: it may contain the missing schedule. This is not fixed yet.

## Verification and sample files

Last full offline run: 56 discovered, 55 passed, one optional DB test skipped.
Latest focused answer run: eight passed. Re-run after changes rather than assuming.
Live examples cover maternity, breastfeeding, overtime arithmetic, annual leave,
incorrect premises, mixed scope, missing inputs, dialect and attempted fake citations.
Several improved outputs coexist with older baselines; filenames alone do not prove
which code generated them. Check prompt_version and contents. Do not silently edit
saved answers to make evaluation pass. JSON output reports can be regenerated.

## Useful commands

```powershell
python -m unittest discover -s tests -q
python -m legal_rag.hybrid_search "ما حقوق العاملة عند الولادة؟" --output hybrid-results.json
python -m legal_rag.answer "ما حقوق العاملة عند الولادة؟" --output answer-maternity.json
```

data/ is ignored by Git: another machine needs the corpus separately. A Git clone
does not transfer the Docker database, generated vectors or .env secrets. Read
all code/docs and inspect missing files before promising reproducibility.
