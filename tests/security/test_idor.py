"""V1 — IDOR : un étudiant ne doit pas voir les notes d'un autre étudiant.

Ce test échoue tant que la faille volontaire V1 est présente (v0.1-vulnerable).
"""

import logging

import pytest

from app.seed import email_for

from ..conftest import OTHER_STUDENT, STUDENT, login

pytestmark = pytest.mark.security


def test_student_cannot_read_another_student_grades(client, user_ids):
    login(client, STUDENT)
    other_id = user_ids[email_for(OTHER_STUDENT)]
    resp = client.get(f"/grades/{other_id}")
    assert resp.status_code in (403, 404), f"IDOR : notes de {OTHER_STUDENT} accessibles (HTTP {resp.status_code})"
    assert OTHER_STUDENT not in resp.get_data(as_text=True)


def test_idor_attempt_is_logged(client, user_ids, caplog):
    login(client, STUDENT)
    other_id = user_ids[email_for(OTHER_STUDENT)]
    with caplog.at_level(logging.INFO, logger="edugrade"):
        client.get(f"/grades/{other_id}")
    denied = [getattr(r, "fields", {}) for r in caplog.records if getattr(r, "fields", {}).get("event") == "access_denied"]
    assert denied, "aucun événement access_denied journalisé pour la tentative d'IDOR"
