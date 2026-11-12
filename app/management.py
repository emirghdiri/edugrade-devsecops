"""Gestion par les enseignants : création de comptes étudiants et de matières."""

from __future__ import annotations

import re
import zlib

import psycopg
from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .db import execute, get_db, query_all, query_one
from .logging_setup import log_event
from .security import role_required

bp = Blueprint("manage", __name__, url_prefix="/teacher")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MIN_PASSWORD_LENGTH = 8


def _clean_name(value: str) -> str:
    return " ".join(value.split())


@bp.app_template_filter("subject_color")
def subject_color(name: str) -> int:
    """Couleur stable (0-4) dérivée du nom de la matière, pour les pastilles de l'interface."""
    return zlib.crc32(name.encode("utf-8")) % 5


@bp.route("/students/new", methods=["GET", "POST"])
@role_required("teacher")
def new_student():
    form = {"name": "", "email": ""}
    if request.method == "POST":
        form = {
            "name": _clean_name(request.form.get("name", "")),
            "email": request.form.get("email", "").strip().lower(),
        }
        password = request.form.get("password", "")
        errors = []
        if not 3 <= len(form["name"]) <= 80:
            errors.append("Le nom doit contenir entre 3 et 80 caractères.")
        if not EMAIL_RE.match(form["email"]) or len(form["email"]) > 120:
            errors.append("Adresse e-mail invalide.")
        elif query_one("SELECT 1 AS found FROM users WHERE email = %s", (form["email"],)):
            errors.append("Un compte existe déjà avec cette adresse e-mail.")
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"Le mot de passe initial doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("teacher/student_form.html", form=form), 400

        try:
            row = execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'student') RETURNING id",
                (form["name"], form["email"], generate_password_hash(password)),
            )
        except psycopg.errors.UniqueViolation:
            get_db().rollback()
            flash("Un compte existe déjà avec cette adresse e-mail.", "error")
            return render_template("teacher/student_form.html", form=form), 400

        log_event("student_created", status=302, student_id=row["id"])
        flash(f"Étudiant {form['name']} ajouté. Communiquez-lui son mot de passe initial.", "success")
        return redirect(url_for("student.grades", student_id=row["id"]))

    return render_template("teacher/student_form.html", form=form)


@bp.route("/subjects", methods=["GET", "POST"])
@role_required("teacher")
def subjects():
    name = ""
    status = 200
    if request.method == "POST":
        name = _clean_name(request.form.get("name", ""))
        if not 2 <= len(name) <= 60:
            flash("Le nom de la matière doit contenir entre 2 et 60 caractères.", "error")
            status = 400
        else:
            row = execute("INSERT INTO subjects (name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", (name,))
            if row is None:
                flash(f"La matière « {name} » existe déjà.", "error")
                status = 400
            else:
                log_event("subject_created", status=302, subject_id=row["id"])
                flash(f"Matière « {name} » ajoutée.", "success")
                return redirect(url_for("manage.subjects"))

    rows = query_all(
        "SELECT s.id, s.name, count(g.id) AS grade_count, avg(g.value) AS average "
        "FROM subjects s LEFT JOIN grades g ON g.subject = s.name "
        "GROUP BY s.id ORDER BY s.name"
    )
    return render_template("teacher/subjects.html", subjects=rows, name=name), status
