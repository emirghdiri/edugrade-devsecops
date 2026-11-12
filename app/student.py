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
    if session.get("role") in ("teacher", "admin"):
        return redirect(url_for("teacher.students" if session["role"] == "teacher" else "admin.users"))
    return redirect(url_for("student.dashboard"))


@bp.route("/dashboard")
@role_required("student")
def dashboard():
    rows = query_all(
        "SELECT subject, value, date FROM grades WHERE student_id = %s ORDER BY date DESC, subject",
        (session["user_id"],),
    )
    best = max(rows, key=lambda g: g["value"], default=None)
    return render_template(
        "student/dashboard.html", count=len(rows), average=_average(rows), best=best, recent=rows[:4]
    )


@bp.route("/grades/<int:student_id>")
@login_required
def grades(student_id: int):
    # Correctif V1 (IDOR) : contrôle d'appartenance côté serveur. Un étudiant ne
    # lit que ses propres notes ; enseignants et administrateur gardent l'accès.
    if session.get("role") == "student" and session.get("user_id") != student_id:
        log_event("access_denied", status=403, level=logging.WARNING, reason="owner", target_student_id=student_id)
        abort(403)
    student = query_one("SELECT id, name, email FROM users WHERE id = %s AND role = 'student'", (student_id,))
    if student is None:
        abort(404)
    rows = query_all(
        "SELECT id, subject, value, date FROM grades WHERE student_id = %s ORDER BY date DESC, subject",
        (student_id,),
    )
    return render_template("student/grades.html", student=student, grades=rows, average=_average(rows))
