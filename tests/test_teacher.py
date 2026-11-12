"""Fonctions enseignant : liste, recherche, ajout et modification de notes."""

import logging
import re

from app.seed import STUDENTS, email_for

from .conftest import TEACHER, csrf, login

ROW = 'data-testid="student-row"'


def test_teacher_lists_all_students(client):
    login(client, TEACHER)
    html = client.get("/teacher/students").get_data(as_text=True)
    assert html.count(ROW) == len(STUDENTS)


def test_teacher_search_by_name(client):
    login(client, TEACHER)
    html = client.get("/teacher/students?q=Martin").get_data(as_text=True)
    assert html.count(ROW) == 1
    assert "Sarah Martin" in html


def test_teacher_search_is_case_insensitive(client):
    login(client, TEACHER)
    assert client.get("/teacher/students?q=mARtin").get_data(as_text=True).count(ROW) == 1


def test_teacher_search_without_match(client):
    login(client, TEACHER)
    html = client.get("/teacher/students?q=Inexistant").get_data(as_text=True)
    assert html.count(ROW) == 0
    assert "Aucun étudiant trouvé" in html


def test_suspicious_search_is_logged(client, caplog):
    login(client, TEACHER)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        client.get("/teacher/students?q=<script>x</script>")
    found = [getattr(r, "fields", {}) for r in caplog.records if getattr(r, "fields", {}).get("event") == "suspicious_input"]
    assert found and "script_tag" in found[0]["patterns"]


def test_teacher_adds_grade(client, user_ids):
    login(client, TEACHER)
    sid = user_ids[email_for("Sarah Martin")]
    form = client.get(f"/teacher/grades/new?student_id={sid}")
    assert form.status_code == 200
    resp = client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Cryptographie", "value": "17.25", "date": "2026-11-05"},
    )
    assert resp.status_code == 302
    html = client.get(f"/grades/{sid}").get_data(as_text=True)
    assert "17.25" in html and "05/11/2026" in html


def test_teacher_add_grade_rejects_out_of_range_value(client, user_ids):
    login(client, TEACHER)
    sid = user_ids[email_for("Sarah Martin")]
    resp = client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Anglais", "value": "25", "date": "2026-11-05"},
    )
    assert resp.status_code == 400
    assert "entre 0 et 20" in resp.get_data(as_text=True)


def test_teacher_add_grade_rejects_unknown_subject(client, user_ids):
    login(client, TEACHER)
    sid = user_ids[email_for("Sarah Martin")]
    resp = client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Astrologie", "value": "12", "date": "2026-11-05"},
    )
    assert resp.status_code == 400


def test_grade_form_for_unknown_student_is_404(client):
    login(client, TEACHER)
    assert client.get("/teacher/grades/new?student_id=999999").status_code == 404


def test_teacher_updates_grade(client, user_ids, caplog):
    login(client, TEACHER)
    sid = user_ids[email_for("Omar Jaziri")]
    html = client.get(f"/grades/{sid}").get_data(as_text=True)
    grade_id = re.search(r"/teacher/grades/(\d+)/edit", html).group(1)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        resp = client.post(
            f"/teacher/grades/{grade_id}/edit",
            data={"csrf_token": csrf(client), "subject": "Réseaux", "value": "13.5", "date": "2026-10-20"},
        )
    assert resp.status_code == 302
    assert "13.50" in client.get(f"/grades/{sid}").get_data(as_text=True)
    events = [getattr(r, "fields", {}) for r in caplog.records]
    updated = [e for e in events if e.get("event") == "grade_updated"]
    assert updated and str(updated[0]["grade_id"]) == grade_id
    assert "13.5" not in str(updated[0])  # la valeur de la note n'est jamais journalisée
