# Instructions for agents working on this project

## Start of a session

- Read HANDOFF.md, README.md, PROGRESS.md, data.md and every document in docs/.
- Inventory the whole repository, including ignored local data when available.
  Read all first-party Python modules, SQL migrations, tests, dependency/configuration
  files and relevant saved test outputs before proposing architectural changes.
  For large source collections, inspect their schema, inventory, coverage and relevant
  records systematically; do not claim to have read every record if you have not.
- Check git status and actual code before relying on older progress entries.
  Do not overwrite user changes. Do not scan .git internals, virtual environments,
  dependency caches or binary assets as if they were project source.
- Never print or copy .env values/API keys/passwords into chat, docs or commits.
  Use .env.example to understand configuration; verify secret presence without
  exposing values. A separate chat does not automatically have the earlier transcript.

## Collaboration

- The user is a Python beginner: explain plainly and give one practical next step
  at a time. When asked to implement, implement and verify, then explain the change
  and exact command to run. Do not silently expand scope.
- Keep HANDOFF.md and the current-state section of PROGRESS.md accurate when
  models, commands, schema, tests or unresolved issues change. Separate historical
  entries from the current implementation.

## Data and RAG rules

- Existing data/ source artifacts are read-only during RAG work. Report suspected
  source issues rather than silently rewriting legal text. New-domain ingestion is
  planned work; inspect the supplied corpus before loading it.
- Preserve units.text. Normalization and chunks are derived copies. Preserve legal
  conditions, identifiers, source URLs, review holds and parent context.
- Never edit an applied SQL migration; add the next migration when required.
- Article numbers repeat between documents. Use unit_id / Maqam document ID plus
  article number, not article_no alone, as the identity.
- New legal fields still need source validation, loading, chunking, keyword text,
  token checks, embedding generation and evaluation. Embedding labour does not embed
  future fields. Follow docs/NEW_DOMAINS.md and use --domain explicitly.
- Keep question and document embedding models compatible: currently
  gemini-embedding-001, 1536 dimensions, normalized; use RETRIEVAL_QUERY for questions
  and RETRIEVAL_DOCUMENT for corpus text. Cache matching uses the full profile/hash.
- Generation uses Gemini with GEMINI_API_KEY and ANSWER_MODEL. Verify current
  defaults in answer.py. Do not revert to historical OpenAI/Groq setup instructions.
- Citation membership checks are not factual verification. Never invent legal
  rules or turn unrelated search matches into a confident answer.

## Verification

- Run tests appropriate to the change. Full offline suite:
  `python -m unittest discover -s tests -q`.
- PostgreSQL integration test is opt-in; distinguish skipped tests from passes.
- Live API tests may use quota and fail temporarily; preserve baselines and save
  comparisons under new filenames. Do not regenerate the full corpus unnecessarily.
