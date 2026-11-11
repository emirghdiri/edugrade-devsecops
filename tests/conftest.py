"""Fixtures communes : application de test branchée sur une base PostgreSQL jetable.

La base est fournie par scripts/test_db.sh (ou par TEST_DATABASE_URL).
"""

from __future__ import annotations

import os
import secrets

import psycopg
import pytest

from app import create_app
from app.config import Config
from app.db import connect
from app.seed import demo_password, email_for, seed_database

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://edugrade:edugrade-test@127.0.0.1:5433/edugrade_test"
)


@pytest.fixture(scope="session")
def app():
    try:
        conn = connect(TEST_DATABASE_URL)
    except psycopg.OperationalError as exc:
        pytest.exit(f"Base de test injoignable ({exc}). Lancez : scripts/test_db.sh start", returncode=2)
    with conn:
        seed_database(conn, Config.SUBJECTS, reset=True)
    return create_app({"TESTING": True, "SECRET_KEY": "tests-uniquement", "DATABASE_URL": TEST_DATABASE_URL})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def user_ids(app) -> dict[str, int]:
    """Identifiants des comptes de démonstration, indexés par e-mail."""
    with connect(TEST_DATABASE_URL) as conn:
        rows = conn.execute("SELECT id, email FROM users").fetchall()
    return {r["email"]: r["id"] for r in rows}


def csrf(client) -> str:
    with client.session_transaction() as sess:
        sess.setdefault("_csrf", secrets.token_urlsafe(32))
        return sess["_csrf"]


def login(client, name: str, password: str | None = None):
    return client.post(
        "/login",
        data={"csrf_token": csrf(client), "email": email_for(name), "password": password or demo_password(name)},
    )


STUDENT = "Lina Ben Salah"
OTHER_STUDENT = "Youssef Trabelsi"
TEACHER = "Claire Dubois"
