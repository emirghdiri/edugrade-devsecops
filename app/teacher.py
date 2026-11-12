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
    # VULN-V2 (volontaire, voir docs/VULNERABILITES.md)
    with get_db().cursor() as cur:
        cur.execute(f"SELECT id, name, email FROM users WHERE role = 'student' AND name ILIKE '%{term}%' ORDER BY name")
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


def _grade_form(student: dict, grade: dict, mode: str) -> str:
    subjects = list_subjects()
    # Une note existante peut porter une matière qui n'est plus proposée : on la garde sélectionnable.
    if grade.get("subject") and grade["subject"] not in subjects:
        subjects.append(grade["subject"])
    return render_template("teacher/grade_form.html", student=student, grade=grade, mode=mode, subjects=subjects)
