"""Administration : gestion des comptes enseignants et étudiants (création, lecture, modification, suppression)."""

from __future__ import annotations

import re

import psycopg
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from .db import execute, get_db, query_all, query_one
from .logging_setup import log_event
from .security import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")

ROLES = {"teacher": "Enseignant", "student": "Étudiant"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
MIN_PASSWORD_LENGTH = 8


def _clean(value: str) -> str:
    return " ".join(value.split())


def _managed_user_or_404(user_id: int) -> dict:
    """Seuls les comptes enseignants et étudiants sont gérés ici (jamais les administrateurs)."""
    user = query_one(
        "SELECT id, name, email, role FROM users WHERE id = %s AND role IN ('teacher', 'student')", (user_id,)
    )
    if user is None:
        abort(404)
    return user


def _validate(form, *, creating: bool, user_id: int | None = None) -> tuple[dict, str, list[str]]:
    data = {
        "name": _clean(form.get("name", "")),
        "email": form.get("email", "").strip().lower(),
        "role": form.get("role", "student"),
    }
    password = form.get("password", "")
    errors: list[str] = []
    if not 3 <= len(data["name"]) <= 80:
        errors.append("Le nom doit contenir entre 3 et 80 caractères.")
    if not EMAIL_RE.match(data["email"]) or len(data["email"]) > 120:
        errors.append("Adresse e-mail invalide.")
    elif query_one("SELECT 1 AS found FROM users WHERE email = %s AND id <> %s", (data["email"], user_id or 0)):
        errors.append("Un compte existe déjà avec cette adresse e-mail.")
    if creating and data["role"] not in ROLES:
        errors.append("Rôle invalide.")
    if (creating or password) and len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")
    return data, password, errors


@bp.route("/users")
@role_required("admin")
def users():
    role = request.args.get("role", "")
    if role not in ROLES:
        role = ""
    rows = query_all(
        "SELECT u.id, u.name, u.email, u.role, count(g.id) AS grade_count "
        "FROM users u LEFT JOIN grades g ON g.student_id = u.id "
        "WHERE u.role IN ('teacher', 'student') AND (%s = '' OR u.role = %s) "
        "GROUP BY u.id ORDER BY u.role DESC, u.name",
        (role, role),
    )
    stats = query_one(
        "SELECT count(*) FILTER (WHERE role = 'teacher') AS teachers, "
        "count(*) FILTER (WHERE role = 'student') AS students, "
        "(SELECT count(*) FROM grades) AS grades FROM users"
    )
    return render_template("admin/users.html", users=rows, role=role, stats=stats, roles=ROLES)


@bp.route("/users/new", methods=["GET", "POST"])
@role_required("admin")
def new_user():
    preset = request.args.get("role", "student")
    data = {"name": "", "email": "", "role": preset if preset in ROLES else "student"}
    if request.method == "POST":
        data, password, errors = _validate(request.form, creating=True)
        if not errors:
            try:
                row = execute(
                    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
                    (data["name"], data["email"], generate_password_hash(password), data["role"]),
                )
            except psycopg.errors.UniqueViolation:
                get_db().rollback()
                errors = ["Un compte existe déjà avec cette adresse e-mail."]
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/user_form.html", user=data, mode="new", roles=ROLES), 400
        log_event("user_created", status=302, target_user_id=row["id"], target_role=data["role"])
        flash(f"{ROLES[data['role']]} {data['name']} ajouté. Communiquez-lui son mot de passe initial.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=data, mode="new", roles=ROLES)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user(user_id: int):
    user = _managed_user_or_404(user_id)
    if request.method == "POST":
        data, password, errors = _validate(request.form, creating=False, user_id=user_id)
        data["role"], data["id"] = user["role"], user_id  # le rôle n'est pas modifiable
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/user_form.html", user=data, mode="edit", roles=ROLES), 400
        if password:
            execute(
                "UPDATE users SET name = %s, email = %s, password_hash = %s WHERE id = %s",
                (data["name"], data["email"], generate_password_hash(password), user_id),
            )
        else:
            execute("UPDATE users SET name = %s, email = %s WHERE id = %s", (data["name"], data["email"], user_id))
        log_event("user_updated", status=302, target_user_id=user_id, password_changed=bool(password))
        flash(f"Compte de {data['name']} modifié.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", user=user, mode="edit", roles=ROLES)


@bp.route("/users/<int:user_id>/delete", methods=["GET", "POST"])
@role_required("admin")
def delete_user(user_id: int):
    user = _managed_user_or_404(user_id)
    grade_count = query_one("SELECT count(*) AS n FROM grades WHERE student_id = %s", (user_id,))["n"]
    if request.method == "POST":
        execute("DELETE FROM users WHERE id = %s", (user_id,))  # les notes d'un étudiant suivent (ON DELETE CASCADE)
        log_event("user_deleted", status=302, target_user_id=user_id, target_role=user["role"], grades_deleted=grade_count)
        flash(f"Compte de {user['name']} supprimé.", "success")
        return redirect(url_for("admin.users"))
    details = [f"{ROLES[user['role']]} : {user['name']} ({user['email']})"]
    if grade_count:
        details.append(f"{grade_count} note(s) associée(s) seront également supprimées.")
    return render_template(
        "confirm_delete.html",
        title="Supprimer un compte",
        message="Cette action est définitive.",
        details=details,
        action=url_for("admin.delete_user", user_id=user_id),
        cancel=url_for("admin.users"),
    )
