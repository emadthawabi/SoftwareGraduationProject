# Agent handoff — current state

Updated: 2026-11-25. This is a working summary, not the full chat transcript.
Read AGENTS.md and verify the repository/database before making changes.

## Project and team

Palestinian legal RAG graduation project with Arabic questions and cited answers.
The user handles AI/RAG; their partner handles the website. Mobile/Flutter is
postponed. The user wants small, clearly explained steps. More legal fields will
be supplied later; do not treat corpus preparation or embeddings as globally done.

## Implemented pipeline

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
