"""V2 — Injection SQL : la recherche enseignant doit traiter la saisie comme une donnée.

Ce test échoue tant que la faille volontaire V2 est présente (v0.1-vulnerable).
"""

import pytest

from ..conftest import TEACHER, login

pytestmark = pytest.mark.security

ROW = 'data-testid="student-row"'


def test_tautology_does_not_return_all_students(client):
    login(client, TEACHER)
    html = client.get("/teacher/students", query_string={"q": "' OR '1'='1"}).get_data(as_text=True)
    assert html.count(ROW) == 0, f"injection SQL : {html.count(ROW)} étudiants renvoyés pour une tautologie"


def test_union_does_not_leak_password_hashes(client):
    login(client, TEACHER)
    payload = "%' UNION SELECT id, name, password_hash FROM users --"
    html = client.get("/teacher/students", query_string={"q": payload}).get_data(as_text=True)
    assert "scrypt:" not in html and "pbkdf2:" not in html, "injection SQL : hachages de mots de passe divulgués"
