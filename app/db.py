"""Accès PostgreSQL (psycopg 3) : une connexion par requête, fermée en fin de requête."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import psycopg
from flask import Flask, current_app, g
from psycopg.rows import dict_row

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(url: str) -> psycopg.Connection:
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=5)


def get_db() -> psycopg.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        if exc is not None:
            conn.rollback()
        conn.close()


def query_all(sql: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
    with get_db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def query_one(sql: str, params: tuple | dict | None = None) -> dict[str, Any] | None:
    with get_db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params: tuple | dict | None = None) -> dict[str, Any] | None:
    """Exécute une écriture, valide la transaction et renvoie la ligne RETURNING éventuelle."""
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone() if cur.description else None
    conn.commit()
    return row


def init_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def ping() -> bool:
    try:
        query_one("SELECT 1 AS ok")
        return True
    except psycopg.Error:
        return False


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
