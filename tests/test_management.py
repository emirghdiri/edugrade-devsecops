"""CRUD : comptes (administrateur), matières et notes (enseignant), contrôle des rôles."""

import logging
import re

import pytest

from .conftest import ADMIN, STUDENT, TEACHER, csrf, login


def _events(caplog, name):
    return [getattr(r, "fields", {}) for r in caplog.records if getattr(r, "fields", {}).get("event") == name]


def _create_user(client, **overrides):
    data = {"role": "student", "name": "Nour Haddad", "email": "nour.haddad@edugrade.test", "password": "nour-initial-1"}
    data.update(overrides)
    return client.post("/admin/users/new", data={"csrf_token": csrf(client), **data})


def _user_id(client, email):
    html = client.get("/admin/users").get_data(as_text=True)
    for row in html.split('data-testid="user-row"')[1:]:
        if email in row:
            return int(re.search(r"/admin/users/(\d+)/edit", row).group(1))
    raise AssertionError(f"{email} absent de la liste")


# ---------- Administrateur : comptes ----------

def test_admin_lands_on_users_page(client):
    login(client, ADMIN)
    assert client.get("/").headers["Location"].endswith("/admin/users")
    html = client.get("/admin/users").get_data(as_text=True)
    assert "Claire Dubois" in html and "Lina Ben Salah" in html


def test_admin_filters_by_role(client):
    login(client, ADMIN)
    html = client.get("/admin/users?role=teacher").get_data(as_text=True)
    assert "Claire Dubois" in html and "Lina Ben Salah" not in html


def test_admin_creates_teacher_and_student_who_can_log_in(client, caplog):
    login(client, ADMIN)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        assert _create_user(client, role="teacher", name="Samir Ayari", email="samir.ayari@edugrade.test").status_code == 302
        assert _create_user(client).status_code == 302
    created = _events(caplog, "user_created")
    assert {e["target_role"] for e in created} == {"teacher", "student"}
    assert "nour-initial-1" not in str(caplog.records)  # jamais de mot de passe dans les journaux

    client.post("/logout", data={"csrf_token": csrf(client)})
    resp = client.post(
        "/login", data={"csrf_token": csrf(client), "email": "samir.ayari@edugrade.test", "password": "nour-initial-1"}
    )
    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["role"] == "teacher"


def test_admin_rejects_invalid_or_duplicate_user(client):
    login(client, ADMIN)
    resp = _create_user(client, email="lina.bensalah@edugrade.test")
    assert resp.status_code == 400 and "existe déjà" in resp.get_data(as_text=True)
    resp = _create_user(client, name="A", email="pas-un-email", password="court")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400 and "entre 3 et 80" in html and "e-mail invalide" in html and "au moins 8" in html
    assert _create_user(client, role="admin", email="pirate@edugrade.test").status_code == 400  # pas de création d'admin


def test_admin_updates_user(client, caplog):
    login(client, ADMIN)
    _create_user(client, name="Temp Modif", email="temp.modif@edugrade.test")
    uid = _user_id(client, "temp.modif@edugrade.test")
    with caplog.at_level(logging.INFO, logger="edugrade"):
        resp = client.post(
            f"/admin/users/{uid}/edit",
            data={"csrf_token": csrf(client), "name": "Temp Modifié", "email": "temp.modifie@edugrade.test", "password": ""},
        )
    assert resp.status_code == 302
    html = client.get("/admin/users").get_data(as_text=True)
    assert "Temp Modifié" in html and "temp.modifie@edugrade.test" in html
    assert _events(caplog, "user_updated")[0]["password_changed"] is False


def test_admin_deletes_student_and_their_grades(client, caplog):
    login(client, ADMIN)
    _create_user(client, name="Temp Supprime", email="temp.supprime@edugrade.test")
    uid = _user_id(client, "temp.supprime@edugrade.test")
    assert "Confirmer la suppression" in client.get(f"/admin/users/{uid}/delete").get_data(as_text=True)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        assert client.post(f"/admin/users/{uid}/delete", data={"csrf_token": csrf(client)}).status_code == 302
    assert "temp.supprime@edugrade.test" not in client.get("/admin/users").get_data(as_text=True)
    assert _events(caplog, "user_deleted")


def test_admin_cannot_manage_admin_accounts(client, user_ids):
    login(client, ADMIN)
    admin_id = user_ids["nadia.mansour@edugrade.test"]
    assert client.get(f"/admin/users/{admin_id}/edit").status_code == 404
    assert client.post(f"/admin/users/{admin_id}/delete", data={"csrf_token": csrf(client)}).status_code == 404


@pytest.mark.parametrize("who", [TEACHER, STUDENT])
def test_non_admin_is_denied_on_admin_pages(client, who):
    login(client, who)
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin/users/new").status_code == 403
    assert _create_user(client, email="intrus@edugrade.test").status_code == 403


# ---------- Enseignant : matières ----------

def test_teacher_lists_default_subjects(client):
    login(client, TEACHER)
    html = client.get("/teacher/subjects").get_data(as_text=True)
    assert html.count('data-testid="subject-row"') >= 5 and "Cryptographie" in html


def _subject_id(client, name):
    html = client.get("/teacher/subjects").get_data(as_text=True)
    for row in html.split('data-testid="subject-row"')[1:]:
        if f">{name}<" in row:
            return int(re.search(r"/teacher/subjects/(\d+)/edit", row).group(1))
    raise AssertionError(f"{name} absente")


def test_teacher_creates_renames_and_deletes_subject(client, user_ids, caplog):
    login(client, TEACHER)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        assert client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "Sécurité web"}).status_code == 302
    assert _events(caplog, "subject_created")

    # une note dans la nouvelle matière, puis renommage : la note suit
    sid = user_ids["sarah.martin@edugrade.test"]
    client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Sécurité web", "value": "18", "date": "2026-11-12"},
    )
    subj = _subject_id(client, "Sécurité web")
    resp = client.post(f"/teacher/subjects/{subj}/edit", data={"csrf_token": csrf(client), "name": "Sécurité des applications web"})
    assert resp.status_code == 302
    grades_html = client.get(f"/grades/{sid}").get_data(as_text=True)
    assert "Sécurité des applications web" in grades_html and ">Sécurité web<" not in grades_html

    # suppression refusée tant qu'une note l'utilise
    client.post(f"/teacher/subjects/{subj}/delete", data={"csrf_token": csrf(client)})
    assert "Impossible de supprimer" in client.get("/teacher/subjects").get_data(as_text=True)

    # matière inutilisée : suppression acceptée
    client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "Matière temporaire"})
    tmp = _subject_id(client, "Matière temporaire")
    assert client.post(f"/teacher/subjects/{tmp}/delete", data={"csrf_token": csrf(client)}).status_code == 302
    assert ">Matière temporaire<" not in client.get("/teacher/subjects").get_data(as_text=True)


def test_duplicate_or_invalid_subject_is_rejected(client):
    login(client, TEACHER)
    resp = client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "  cryptographie "})
    assert resp.status_code == 400 and "existe déjà" in resp.get_data(as_text=True)
    assert client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "X"}).status_code == 400


def test_student_cannot_manage_subjects(client):
    login(client, STUDENT)
    assert client.get("/teacher/subjects").status_code == 403
    assert client.post("/teacher/subjects", data={"csrf_token": csrf(client), "name": "Intrusion"}).status_code == 403


# ---------- Enseignant : suppression de note ----------

def test_teacher_deletes_grade(client, user_ids, caplog):
    login(client, TEACHER)
    sid = user_ids["emma.lefevre@edugrade.test"]
    client.post(
        f"/teacher/grades/new?student_id={sid}",
        data={"csrf_token": csrf(client), "subject": "Anglais", "value": "4.75", "date": "2026-11-12"},
    )
    html = client.get(f"/grades/{sid}").get_data(as_text=True)
    row = next(r for r in html.split('data-testid="grade-row"')[1:] if ">4.75<" in r)
    grade_id = re.search(r"/teacher/grades/(\d+)/delete", row).group(1)
    assert "Confirmer la suppression" in client.get(f"/teacher/grades/{grade_id}/delete").get_data(as_text=True)
    with caplog.at_level(logging.INFO, logger="edugrade"):
        assert client.post(f"/teacher/grades/{grade_id}/delete", data={"csrf_token": csrf(client)}).status_code == 302
    assert ">4.75<" not in client.get(f"/grades/{sid}").get_data(as_text=True)
    deleted = _events(caplog, "grade_deleted")
    assert deleted and "4.75" not in str(deleted[0])  # la valeur n'est jamais journalisée


def test_student_cannot_delete_grade(client, user_ids):
    login(client, STUDENT)
    assert client.post("/teacher/grades/1/delete", data={"csrf_token": csrf(client)}).status_code == 403
