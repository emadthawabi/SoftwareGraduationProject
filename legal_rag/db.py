"""Database connection, configured from the environment (.env)."""

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("Set DATABASE_URL or POSTGRES_PASSWORD in .env")
    return f"postgresql://legaluser:{password}@127.0.0.1:5433/legalai"


def connect() -> psycopg.Connection:
    return psycopg.connect(database_url())
