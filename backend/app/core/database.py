import sqlite3, re
from contextlib import contextmanager
from pathlib import Path
from .config import DATA, DATABASE_URL

PG = bool(DATABASE_URL)


@contextmanager
def db():
    if PG:
        import psycopg

        conn = psycopg.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect(DATA / "documind.db", timeout=30)
        conn.execute("PRAGMA foreign_keys=ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def sql(conn, query, args=()):
    if PG:
        query = re.sub(
            r"\b(users|sessions|documents|chunks|conversations|messages|usage)\b",
            r"dm_\1",
            query,
        )
        query = query.replace("?", "%s")
    return conn.execute(query, args)


def initialize():
    migration = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / ("001_postgres.sql" if PG else "001_sqlite.sql")
    )
    with db() as conn:
        for statement in migration.read_text().split(";"):
            if statement.strip():
                conn.execute(statement)
        # Small, additive upgrade for existing local previews; no uploaded data is removed.
        columns = (
            [
                r[0]
                for r in conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='dm_messages'"
                ).fetchall()
            ]
            if PG
            else [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
        )
        if "ordinal" not in columns:
            sql(
                conn,
                "ALTER TABLE messages ADD COLUMN ordinal INTEGER NOT NULL DEFAULT 0",
            )
