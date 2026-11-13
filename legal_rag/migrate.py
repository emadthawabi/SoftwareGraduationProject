"""Apply SQL migrations in database/migrations/ in filename order.

Each file runs once, inside its own transaction; applied files are recorded
in the schema_migrations table.

Usage: python -m legal_rag.migrate
"""

from pathlib import Path

from legal_rag.db import connect

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "database" / "migrations"


def main() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        conn.commit()
        applied = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}

        pending = [p for p in sorted(MIGRATIONS_DIR.glob("*.sql")) if p.name not in applied]
        if not pending:
            print("Database is up to date.")
            return

        for path in pending:
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            print(f"applied {path.name}")


if __name__ == "__main__":
    main()
