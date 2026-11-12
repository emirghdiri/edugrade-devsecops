"""Gestion par l'enseignant : création d'étudiants et de matières."""

import logging

from .conftest import STUDENT, TEACHER, csrf, login


def _new_student(client, **overrides):
    data = {"name": "Nour Haddad", "email": "nour.haddad@edugrade.test", "password": "nour-initial-1"}
    data.update(overrides)
    return client.post("/teacher/students/new", data={"csrf_token": csrf(client), **data})


def test_teacher_sees_student_form(client):
    login(client, TEACHER)
    resp = client.get("/teacher/students/new")
    assert resp.status_code == 200
    assert "Ajouter un étudiant" in resp.get_data(as_text=True)


def test_teacher_creates_student_who_can_log_in(client, caplog):
    login(client, TEACHER)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        resp = _new_student(client)
    assert resp.status_code == 302
    events = [getattr(r, "fields", {}) for r in caplog.records]
    created = [e for e in events if e.get("event") == "student_created"]
    assert created and "nour-initial-1" not in str(events)  # jamais de mot de passe dans les journaux

    # le nouvel étudiant apparaît dans la liste et peut se connecter
    assert "Nour Haddad" in client.get("/teacher/students").get_data(as_text=True)
    client.post("/logout", data={"csrf_token": csrf(client)})
    resp = client.post(
        "/login", data={"csrf_token": csrf(client), "email": "nour.haddad@edugrade.test", "password": "nour-initial-1"}
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["role"] == "student"


def test_duplicate_email_is_rejected(client):
    login(client, TEACHER)
    resp = _new_student(client, email="lina.bensalah@edugrade.test")
    assert resp.status_code == 400
    assert "existe déjà" in resp.get_data(as_text=True)


def test_invalid_student_data_is_rejected(client):
    login(client, TEACHER)
    resp = _new_student(client, name="A", email="pas-un-email", password="court")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert "entre 3 et 80" in html and "e-mail invalide" in html and "au moins 8" in html


def test_student_cannot_create_students_or_subjects(client):
    login(client, STUDENT)
    assert client.get("/teacher/students/new").status_code == 403
    assert _new_student(client, email="intrus@edugrade.test").status_code == 403
    assert client.get("/teacher/subjects").status_code == 403
    resp = client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "Intrusion"})
    assert resp.status_code == 403


def test_teacher_lists_default_subjects(client):
    login(client, TEACHER)
    html = client.get("/teacher/subjects").get_data(as_text=True)
    assert html.count('data-testid="subject-row"') >= 5
    assert "Cryptographie" in html


def test_teacher_creates_subject_then_grades_it(client, user_ids, caplog):
    login(client, TEACHER)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        resp = client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "Sécurité des applications"})
    assert resp.status_code == 302
    assert any(getattr(r, "fields", {}).get("event") == "subject_created" for r in caplog.records)

    sid = user_ids["sarah.martin@edugrade.test"]
    assert "Sécurité des applications" in client.get(f"/teacher/grades/new?student_id={sid}").get_data(as_text=True)
    resp = client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Sécurité des applications", "value": "18", "date": "2026-11-12"},
    )
    assert resp.status_code == 302
    assert "Sécurité des applications" in client.get(f"/grades/{sid}").get_data(as_text=True)


def test_duplicate_subject_is_rejected_case_insensitively(client):
    login(client, TEACHER)
    resp = client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "  cryptographie "})
    assert resp.status_code == 400
    assert "existe déjà" in resp.get_data(as_text=True)


def test_too_short_subject_is_rejected(client):
    login(client, TEACHER)
    resp = client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "X"})
    assert resp.status_code == 400
