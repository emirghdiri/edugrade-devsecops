"""Crée le schéma et charge le jeu de données de démonstration (entièrement fictif).

Usage : python -m app.seed [--reset]

Comptes : e-mail prénom.nom@edugrade.test ; mot de passe de démonstration =
prénom en minuscules sans accent suivi de 2026 (voir README). Les mots de passe
ne sont stockés que sous forme de hachage (werkzeug).
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
import unicodedata
from datetime import date, timedelta

import psycopg
from psycopg.rows import tuple_row
from werkzeug.security import generate_password_hash

from .config import Config, build_database_url
from .db import connect, init_schema
from .logging_setup import LOGGER_NAME, configure_logging

TEACHERS = ["Claire Dubois", "Karim Haddad"]
STUDENTS = ["Lina Ben Salah", "Youssef Trabelsi", "Sarah Martin", "Omar Jaziri", "Emma Lefèvre", "Mehdi Gharbi"]

log = logging.getLogger(LOGGER_NAME)


def _ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def email_for(name: str) -> str:
    first, *rest = _ascii(name).split()
    return f"{first}.{''.join(rest)}@edugrade.test"


def demo_password(name: str) -> str:
    return f"{_ascii(name).split()[0]}2026"


def seed_database(conn: psycopg.Connection, subjects: list[str], reset: bool = False) -> bool:
    """Renvoie True si les données ont été insérées, False si la base était déjà peuplée."""
    with conn.transaction():
        if reset:
            conn.execute("DROP TABLE IF EXISTS grades, users, subjects CASCADE")
        init_schema(conn)
        cur = conn.cursor(row_factory=tuple_row)
        # Matières par défaut (settings.yaml) : ajoutées si absentes, même sur une base existante.
        for name in subjects:
            cur.execute("INSERT INTO subjects (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
        if cur.execute("SELECT count(*) FROM users").fetchone()[0]:
            return False

        def add_user(name: str, role: str) -> int:
            row = cur.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, email_for(name), generate_password_hash(demo_password(name)), role),
            ).fetchone()
            return row[0]

        for name in TEACHERS:
            add_user(name, "teacher")

        rng = random.Random(2026)  # jeu de données reproductible
        start = date(2026, 9, 15)
        for name in STUDENTS:
            student_id = add_user(name, "student")
            for subject in rng.sample(subjects, rng.choice([4, 5])):
                value = round(rng.uniform(6, 19) * 4) / 4
                when = start + timedelta(days=rng.randint(0, 55))
                cur.execute(
                    "INSERT INTO grades (student_id, subject, value, date) VALUES (%s, %s, %s, %s)",
                    (student_id, subject, value, when),
                )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="supprime et recrée les tables")
    args = parser.parse_args(argv)

    configure_logging(Config.LOG_LEVEL)
    cfg = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    url = build_database_url(cfg)

    # La base peut mettre quelques secondes à accepter les connexions.
    for attempt in range(1, 31):
        try:
            conn = connect(url)
            break
        except psycopg.OperationalError:
            log.warning("db_unavailable", extra={"fields": {"event": "db_unavailable", "attempt": attempt}})
            time.sleep(2)
    else:
        return 1

    with conn:
        created = seed_database(conn, cfg["SUBJECTS"], reset=args.reset)
    event = "seed_completed" if created else "seed_skipped"
    log.info(event, extra={"fields": {"event": event, "teachers": len(TEACHERS), "students": len(STUDENTS)}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
