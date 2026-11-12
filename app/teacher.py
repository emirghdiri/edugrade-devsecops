"""Espace enseignant : liste et recherche d'étudiants, ajout et modification de notes."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .db import execute, get_db, list_subjects, query_all, query_one
from .logging_setup import detect_suspicious, log_event
from .security import role_required

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


def search_students(term: str) -> list[dict]:
    # Correctif V2 (injection SQL) : le terme est un paramètre lié, jamais
    # concaténé à la requête. Les jokers LIKE saisis (%, _) sont échappés pour
    # être cherchés tels quels.
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with get_db().cursor() as cur:
        cur.execute(
            "SELECT id, name, email FROM users WHERE role = 'student' AND name ILIKE %s ORDER BY name",
            (f"%{escaped}%",),
        )
        return cur.fetchall()


@bp.route("/students")
@role_required("teacher")
def students():
    q = request.args.get("q", "").strip()
    error = None
    status = 200
    if q:
        patterns = detect_suspicious(q)
        if patterns:
            log_event("suspicious_input", status=200, level=logging.WARNING, field="q", patterns=patterns, length=len(q))
        try:
            rows = search_students(q)
        except psycopg.Error:
            get_db().rollback()
            log_event("db_error", status=500, level=logging.ERROR, context="student_search")
            rows, error, status = [], "La recherche a échoué.", 500
    else:
        rows = query_all(
            "SELECT u.id, u.name, u.email, count(g.id) AS grade_count, avg(g.value) AS average "
            "FROM users u LEFT JOIN grades g ON g.student_id = u.id "
            "WHERE u.role = 'student' GROUP BY u.id ORDER BY u.name"
        )
    overview = query_one("SELECT count(*) AS grades, avg(value) AS average FROM grades") if not q else None
    return render_template("teacher/students.html", students=rows, q=q, error=error, overview=overview), status


def _student_or_404(student_id: int | None) -> dict:
    student = None
    if student_id is not None:
        student = query_one("SELECT id, name FROM users WHERE id = %s AND role = 'student'", (student_id,))
    if student is None:
        abort(404)
    return student


def _validate_grade(form) -> tuple[dict, list[str]]:
    errors: list[str] = []
    subjects = list_subjects()

    subject = form.get("subject", "")
    if subject not in subjects:
        errors.append("Matière inconnue.")

    try:
        value = Decimal(form.get("value", "").replace(",", "."))
        if not value.is_finite() or not (Decimal(0) <= value <= Decimal(20)):
            raise InvalidOperation
        value = value.quantize(Decimal("0.01"))
    except InvalidOperation:
        errors.append("La note doit être un nombre entre 0 et 20.")
        value = None

    try:
        when = date.fromisoformat(form.get("date", ""))
    except ValueError:
        errors.append("Date invalide.")
        when = None

    return {"subject": subject, "value": value, "date": when}, errors


@bp.route("/grades/new", methods=["GET", "POST"])
@role_required("teacher")
def new_grade():
    student = _student_or_404(request.values.get("student_id", type=int))
    grade = {"subject": "", "value": "", "date": date.today()}

    if request.method == "POST":
        grade, errors = _validate_grade(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return _grade_form(student, grade, "new"), 400
        row = execute(
            "INSERT INTO grades (student_id, subject, value, date) VALUES (%s, %s, %s, %s) RETURNING id",
            (student["id"], grade["subject"], grade["value"], grade["date"]),
        )
        log_event("grade_created", status=302, grade_id=row["id"], student_id=student["id"])
        flash(f"Note ajoutée pour {student['name']}.", "success")
        return redirect(url_for("student.grades", student_id=student["id"]))

    return _grade_form(student, grade, "new")


@bp.route("/grades/<int:grade_id>/edit", methods=["GET", "POST"])
@role_required("teacher")
def edit_grade(grade_id: int):
    grade = query_one("SELECT id, student_id, subject, value, date FROM grades WHERE id = %s", (grade_id,))
    if grade is None:
        abort(404)
    student = _student_or_404(grade["student_id"])

    if request.method == "POST":
        data, errors = _validate_grade(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            data["id"] = grade_id
            return _grade_form(student, data, "edit"), 400
        execute(
            "UPDATE grades SET subject = %s, value = %s, date = %s WHERE id = %s",
            (data["subject"], data["value"], data["date"], grade_id),
        )
        log_event("grade_updated", status=302, grade_id=grade_id, student_id=student["id"])
        flash(f"Note modifiée pour {student['name']}.", "success")
        return redirect(url_for("student.grades", student_id=student["id"]))

    return _grade_form(student, grade, "edit")


@bp.route("/grades/<int:grade_id>/delete", methods=["GET", "POST"])
@role_required("teacher")
def delete_grade(grade_id: int):
    grade = query_one(
        "SELECT g.id, g.student_id, g.subject, g.value, g.date, u.name AS student_name "
        "FROM grades g JOIN users u ON u.id = g.student_id WHERE g.id = %s",
        (grade_id,),
    )
    if grade is None:
        abort(404)
    if request.method == "POST":
        execute("DELETE FROM grades WHERE id = %s", (grade_id,))
        log_event("grade_deleted", status=302, grade_id=grade_id, student_id=grade["student_id"])
        flash(f"Note supprimée pour {grade['student_name']}.", "success")
        return redirect(url_for("student.grades", student_id=grade["student_id"]))
    return render_template(
        "confirm_delete.html",
        title="Supprimer une note",
        message="Cette action est définitive.",
        details=[
            f"Étudiant : {grade['student_name']}",
            f"{grade['subject']} — {grade['value']:.2f} / 20 — {grade['date'].strftime('%d/%m/%Y')}",
        ],
        action=url_for("teacher.delete_grade", grade_id=grade_id),
        cancel=url_for("student.grades", student_id=grade["student_id"]),
    )


def _grade_form(student: dict, grade: dict, mode: str) -> str:
    subjects = list_subjects()
    # Une note existante peut porter une matière qui n'est plus proposée : on la garde sélectionnable.
    if grade.get("subject") and grade["subject"] not in subjects:
        subjects.append(grade["subject"])
    return render_template("teacher/grade_form.html", student=student, grade=grade, mode=mode, subjects=subjects)
