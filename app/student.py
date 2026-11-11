"""Espace étudiant : tableau de bord et consultation des notes."""

from __future__ import annotations

import logging

from flask import Blueprint, abort, redirect, render_template, session, url_for

from .db import query_all, query_one
from .logging_setup import log_event
from .security import login_required, role_required

bp = Blueprint("student", __name__)


def _average(grades: list[dict]) -> float | None:
    if not grades:
        return None
    return sum(float(g["value"]) for g in grades) / len(grades)


@bp.route("/")
@login_required
def index():
    if session.get("role") == "teacher":
        return redirect(url_for("teacher.students"))
    return redirect(url_for("student.dashboard"))


@bp.route("/dashboard")
@role_required("student")
def dashboard():
    grades = query_all("SELECT value FROM grades WHERE student_id = %s", (session["user_id"],))
    return render_template("student/dashboard.html", count=len(grades), average=_average(grades))


@bp.route("/grades/<int:student_id>")
@login_required
def grades(student_id: int):
    # Un étudiant ne consulte que ses propres notes ; un enseignant les consulte toutes.
    if session.get("role") == "student" and session.get("user_id") != student_id:
        log_event("access_denied", status=403, level=logging.WARNING, reason="not_owner", target_student_id=student_id)
        abort(403)

    student = query_one("SELECT id, name, email FROM users WHERE id = %s AND role = 'student'", (student_id,))
    if student is None:
        abort(404)
    rows = query_all(
        "SELECT id, subject, value, date FROM grades WHERE student_id = %s ORDER BY date DESC, subject",
        (student_id,),
    )
    return render_template("student/grades.html", student=student, grades=rows, average=_average(rows))
