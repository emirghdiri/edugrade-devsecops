"""Configuration de l'application, lue depuis les variables d'environnement."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from psycopg.conninfo import make_conninfo

SETTINGS_PATH = Path(__file__).with_name("settings.yaml")


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    """Charge les paramètres fonctionnels (matières, barème) depuis le fichier YAML."""
    with open(path, encoding="utf-8") as fh:
        return yaml.full_load(fh) or {}


SETTINGS = load_settings()

# Correctif V3 : aucun secret dans le code. Les valeurs viennent uniquement de
# l'environnement (.env en local, GitHub Secrets en CI, Secret Kubernetes en
# cluster). Sans SECRET_KEY, create_app() refuse de démarrer. Les anciennes
# valeurs écrites en dur ne sont plus utilisées nulle part (rotation).


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "db")
    POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "edugrade")
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "edugrade")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
    # DATABASE_URL, si elle est fournie, prime sur les variables POSTGRES_*.
    DATABASE_URL = os.environ.get("DATABASE_URL")

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    SESSION_COOKIE_NAME = "edugrade_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 3600  # secondes

    SUBJECTS = list(SETTINGS.get("subjects", []))


def build_database_url(cfg: dict) -> str:
    if cfg.get("DATABASE_URL"):
        return cfg["DATABASE_URL"]
    return make_conninfo(
        host=cfg["POSTGRES_HOST"],
        port=cfg["POSTGRES_PORT"],
        dbname=cfg["POSTGRES_DB"],
        user=cfg["POSTGRES_USER"],
        password=cfg["POSTGRES_PASSWORD"] or "",
    )
