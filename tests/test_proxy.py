"""IP cliente journalisée derrière les reverse proxys (TRUSTED_PROXY_COUNT)."""

import logging

import pytest

from app import create_app

from .conftest import TEST_DATABASE_URL

CLIENT = "203.0.113.7"  # IP du client (plage de documentation RFC 5737)
TRAEFIK = "10.42.0.9"  # pod Traefik
NGINX = "10.42.0.20"  # pod Nginx (REMOTE_ADDR vu par Gunicorn)


def _logged_ip(app, caplog, xff: str) -> str:
    with caplog.at_level(logging.INFO, logger="edugrade"):
        app.test_client().get("/login", headers={"X-Forwarded-For": xff}, environ_base={"REMOTE_ADDR": NGINX})
    events = [getattr(r, "fields", {}) for r in caplog.records if getattr(r, "fields", {}).get("event") == "http_request"]
    assert events, "aucun événement http_request journalisé"
    return events[-1]["ip"]


def _app(count):
    return create_app({"TESTING": True, "SECRET_KEY": "tests-uniquement", "DATABASE_URL": TEST_DATABASE_URL,
                       "TRUSTED_PROXY_COUNT": count})


def test_compose_one_proxy(app, caplog):
    # Docker Compose : Nginx -> Flask. X-Forwarded-For = « client ».
    assert _logged_ip(_app("1"), caplog, CLIENT) == CLIENT


def test_k3s_two_proxies_logs_real_client(app, caplog):
    # k3s : Traefik écrit « client », Nginx ajoute « traefik ».
    assert _logged_ip(_app("2"), caplog, f"{CLIENT}, {TRAEFIK}") == CLIENT


def test_k3s_with_one_proxy_logs_traefik(app, caplog):
    # Ancien réglage dans k3s : c'est l'IP de Traefik qui était journalisée.
    assert _logged_ip(_app("1"), caplog, f"{CLIENT}, {TRAEFIK}") == TRAEFIK


def test_forged_header_does_not_choose_ip(app, caplog):
    # Un client forge X-Forwarded-For : avec 2 proxys, seule la valeur ajoutée
    # par Traefik (l'IP vue par Traefik) est retenue, pas la valeur forgée.
    assert _logged_ip(_app("2"), caplog, f"6.6.6.6, {CLIENT}, {TRAEFIK}") == CLIENT


@pytest.mark.parametrize("bad", ["0", "4", "deux", ""])
def test_invalid_proxy_count_is_refused(bad):
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY_COUNT"):
        _app(bad)
