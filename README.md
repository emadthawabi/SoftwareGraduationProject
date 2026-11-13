# Palestinian Legal RAG

A retrieval-augmented generation (RAG) system over Palestinian legislation. Given a question in Arabic, it finds the relevant المواد (articles) and answers only from them, with citations.

- **Phase 1 (current):** retrieve the relevant legal texts for a user's question.
- **Phase 2:** extract facts and legal issues from real cases and retrieve the texts that apply to them.

The pipeline is built first on **قانون العمل الفلسطيني رقم (7) لسنة 2000** (Palestinian Labour Law No. 7 of 2000) and its 36 related instruments. Other laws are added later as new domains, with no change to the pipeline.

See [PROGRESS.md](PROGRESS.md) for the current status and decisions, and [docs/DATA_GUIDE.md](docs/DATA_GUIDE.md) for an explanation of the data.

## Pipeline

```
Question ─► Query processing ─► Hybrid search ─► Merge (RRF) ─► Rerank ─► Link expansion ─► Answer with citations
            (normalize, rewrite,  (vector + keyword)                       (references,
             direct lookup)                                                 delegation)
```

The original texts live in PostgreSQL as the source of truth. Search indexes (chunks, embeddings, full-text) are derived from them and can be rebuilt at any time.

## Stack

| Part | Choice |
|---|---|
| Language | Python 3 |
| Database | PostgreSQL 16 + pgvector, in Docker |
| LLM (query rewriting, answers) | OpenAI API |
| Embeddings | OpenAI API |

## Project layout

```
data/corpus/<domain>/          Input data: legislation.jsonl + units.jsonl (see data.md)
database/migrations/           Numbered SQL migrations, applied in order
legal_rag/db.py                Database connection (reads .env)
legal_rag/migrate.py           Applies pending migrations
legal_rag/load.py              Loads a corpus folder into the database
docs/                          Documentation
```

## Data

The `data/` folder is **not in the repository** (it is in `.gitignore`). Get it from the team and place it at the project root so that these files exist:

```
data/corpus/labour/legislation.jsonl
data/corpus/labour/units.jsonl
```

Its format is described in [data.md](data.md) and explained in [docs/DATA_GUIDE.md](docs/DATA_GUIDE.md).

## Setup

Requirements: Docker with Compose, Python 3, and the `data/` folder (see above).

```bash
# 1. Configuration: copy, then set POSTGRES_PASSWORD in .env
cp .env.example .env

# 2. Start the database
sudo docker compose up -d

# 3. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Create the tables
python -m legal_rag.migrate

# 5. Load the labour law corpus
python -m legal_rag.load data/corpus/labour --expect-searchable 405
```

Notes:
- The password in `.env` is applied only when the database volume is first created. Changing it afterwards does not change the database password.
- In zsh, do not paste commands with trailing `# comments`: interactive zsh does not treat `#` as a comment by default.

## Common commands

| Command | Purpose |
|---|---|
| `python -m legal_rag.migrate` | Apply new migrations (safe to re-run) |
| `python -m legal_rag.load data/corpus/labour --expect-searchable 405` | Reload a domain (deletes and reinserts it in one transaction) |
| `sudo docker compose ps` | Container status |
| `sudo docker compose stop` / `up -d` | Stop / start the database (data is kept) |
| `sudo docker exec -it palestinian_legal_db psql -U legaluser -d legalai` | Open a SQL console |

`sudo docker compose down -v` **deletes the database volume and all data**.

## Changing the schema

Never edit a migration that has already been applied. Add a new file with the next number (e.g. `004_....sql`) and run `python -m legal_rag.migrate`.

## Data rules

- The files in `data/` are read-only. Problems are reported, not fixed in place.
- The `text` of a unit is the original wording and is never modified. Normalization happens only in separate search copies.
- The database is a copy of `data/corpus/`. Do not edit it by hand; the next load overwrites it.
