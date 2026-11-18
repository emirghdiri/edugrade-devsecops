"""Accès par rôle : un étudiant ne peut pas utiliser les routes enseignant."""

import logging

import pytest

from app.seed import email_for

from .conftest import OTHER_STUDENT, STUDENT, TEACHER, csrf, login

TEACHER_ROUTES = ["/teacher/students", "/teacher/students?q=Martin"]


@pytest.mark.parametrize("route", TEACHER_ROUTES)
def test_student_is_denied_on_teacher_routes(client, route):
    login(client, STUDENT)
    assert client.get(route).status_code == 403


def test_student_cannot_open_grade_form(client, user_ids):
    login(client, STUDENT)
    sid = user_ids[email_for(STUDENT)]
    assert client.get(f"/teacher/grades/new?student_id={sid}").status_code == 403


def test_student_cannot_post_a_grade(client, user_ids):
    login(client, STUDENT)
    sid = user_ids[email_for(STUDENT)]
    resp = client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Anglais", "value": "20", "date": "2026-11-01"},
    )
    assert resp.status_code == 403


def test_access_denied_is_logged(client, caplog):
    login(client, STUDENT)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        client.get("/teacher/students")
    events = [getattr(r, "fields", {}).get("event") for r in caplog.records]
    assert "access_denied" in events


def test_teacher_cannot_open_student_dashboard(client):
    login(client, TEACHER)
    assert client.get("/dashboard").status_code == 403


def test_student_sees_own_grades(client, user_ids):
    login(client, STUDENT)
    sid = user_ids[email_for(STUDENT)]
    resp = client.get(f"/grades/{sid}")
    assert resp.status_code == 200
    assert STUDENT in resp.get_data(as_text=True)
    assert resp.get_data(as_text=True).count('data-testid="grade-row"') >= 4


def test_teacher_sees_any_student_grades(client, user_ids):
    login(client, TEACHER)
    assert client.get(f"/grades/{user_ids[email_for(OTHER_STUDENT)]}").status_code == 200


def test_dashboard_links_to_own_grades(client, user_ids):
    login(client, STUDENT)
    sid = user_ids[email_for(STUDENT)]
    assert f'href="/grades/{sid}"' in client.get("/dashboard").get_data(as_text=True)
