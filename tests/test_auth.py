"""Connexion, déconnexion et protection des formulaires."""

import json
import logging

from app.seed import email_for

from .conftest import STUDENT, TEACHER, csrf, login


def test_login_page(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Connexion" in resp.get_data(as_text=True)


def test_anonymous_is_redirected_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_success_student(client):
    resp = login(client, STUDENT)
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["role"] == "student"
    assert client.get("/", follow_redirects=False).headers["Location"].endswith("/dashboard")


def test_login_success_teacher(client):
    resp = login(client, TEACHER)
    assert resp.status_code == 302
    assert client.get("/").headers["Location"].endswith("/teacher/students")


def test_login_failed(client):
    resp = login(client, STUDENT, password="mauvais-mot-de-passe")
    assert resp.status_code == 401
    assert "Identifiants invalides" in resp.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_user(client):
    resp = client.post("/login", data={"csrf_token": csrf(client), "email": "inconnu@edugrade.test", "password": "x"})
    assert resp.status_code == 401


def test_post_without_csrf_token_is_rejected(client):
    resp = client.post("/login", data={"email": email_for(STUDENT), "password": "x"})
    assert resp.status_code == 400


def test_logout(client):
    login(client, STUDENT)
    resp = client.post("/logout", data={"csrf_token": csrf(client)})
    assert resp.status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_login_failed_is_logged_without_password(client, caplog):
    with caplog.at_level(logging.INFO, logger="edugrade"):
        login(client, STUDENT, password="secret-a-ne-pas-journaliser")
    events = [getattr(r, "fields", {}) for r in caplog.records]
    failed = [e for e in events if e.get("event") == "login_failed"]
    assert failed and failed[0]["status"] == 401 and failed[0]["route"] == "/login"
    assert "secret-a-ne-pas-journaliser" not in json.dumps(events, default=str)
