"""Connessione Postgres e applicazione delle migrazioni."""
from __future__ import annotations

import os
import pathlib

import psycopg
from psycopg.rows import dict_row

MIGRATIONS_DIR = pathlib.Path(__file__).resolve().parent.parent / "migrations"


def connect(dsn: str | None = None, autocommit: bool = True) -> psycopg.Connection:
    """Sempre autocommit: le transazioni sono SOLO quelle esplicite (conn.transaction()) del motore."""
    dsn = dsn or os.environ.get("WMS_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Manca WMS_DATABASE_URL (o DATABASE_URL)")
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=autocommit)
    return conn


def apply_migrations(conn: psycopg.Connection) -> list[str]:
    """Applica in ordine le migrazioni non ancora registrate. Ogni file è una transazione."""
    conn.execute("CREATE TABLE IF NOT EXISTS public.wms_schema_migrations ("
                 " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
    conn.commit()
    done = {r["name"] for r in conn.execute("SELECT name FROM public.wms_schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        sql = path.read_text(encoding="utf-8")
        # i file contengono BEGIN/COMMIT propri
        conn.execute(sql)
        conn.execute("INSERT INTO public.wms_schema_migrations(name) VALUES (%s)", (path.name,))
        conn.commit()
        applied.append(path.name)
    return applied
