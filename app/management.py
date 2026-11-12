"""Gestion des matières par les enseignants (création, lecture, modification, suppression)."""

from __future__ import annotations

import zlib

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .db import execute, get_db, query_all, query_one
from .logging_setup import log_event
from .security import role_required

bp = Blueprint("manage", __name__, url_prefix="/teacher")


def _clean_name(value: str) -> str:
    return " ".join(value.split())


@bp.app_template_filter("subject_color")
def subject_color(name: str) -> int:
    """Couleur stable (0-4) dérivée du nom de la matière, pour les pastilles de l'interface."""
    return zlib.crc32(name.encode("utf-8")) % 5


def _subject_or_404(subject_id: int) -> dict:
    subject = query_one(
        "SELECT s.id, s.name, (SELECT count(*) FROM grades g WHERE g.subject = s.name) AS grade_count "
        "FROM subjects s WHERE s.id = %s",
        (subject_id,),
    )
    if subject is None:
        abort(404)
    return subject


def _name_error(name: str, exclude_id: int = 0) -> str | None:
    if not 2 <= len(name) <= 60:
        return "Le nom de la matière doit contenir entre 2 et 60 caractères."
    if query_one("SELECT 1 AS found FROM subjects WHERE lower(name) = lower(%s) AND id <> %s", (name, exclude_id)):
        return f"La matière « {name} » existe déjà."
    return None


@bp.route("/subjects", methods=["GET", "POST"])
@role_required("teacher")
def subjects():
    name = ""
    status = 200
    if request.method == "POST":
        name = _clean_name(request.form.get("name", ""))
        error = _name_error(name)
        row = None
        if not error:
            row = execute("INSERT INTO subjects (name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id", (name,))
            if row is None:
                error = f"La matière « {name} » existe déjà."
        if error:
            flash(error, "error")
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


@bp.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
@role_required("teacher")
def edit_subject(subject_id: int):
    subject = _subject_or_404(subject_id)
    if request.method == "POST":
        new_name = _clean_name(request.form.get("name", ""))
        error = _name_error(new_name, exclude_id=subject_id)
        if error:
            flash(error, "error")
            return render_template("teacher/subject_form.html", subject={**subject, "name": new_name}), 400
        # Renommage et mise à jour des notes existantes dans la même transaction.
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("UPDATE subjects SET name = %s WHERE id = %s", (new_name, subject_id))
            cur.execute("UPDATE grades SET subject = %s WHERE subject = %s", (new_name, subject["name"]))
            moved = cur.rowcount
        conn.commit()
        log_event("subject_updated", status=302, subject_id=subject_id, grades_updated=moved)
        flash(f"Matière renommée en « {new_name} » ({moved} note(s) mise(s) à jour).", "success")
        return redirect(url_for("manage.subjects"))
    return render_template("teacher/subject_form.html", subject=subject)


@bp.route("/subjects/<int:subject_id>/delete", methods=["GET", "POST"])
@role_required("teacher")
def delete_subject(subject_id: int):
    subject = _subject_or_404(subject_id)
    if subject["grade_count"]:
        flash(
            f"Impossible de supprimer « {subject['name']} » : {subject['grade_count']} note(s) l'utilisent. "
            "Supprimez ou modifiez d'abord ces notes.",
            "error",
        )
        return redirect(url_for("manage.subjects"))
    if request.method == "POST":
        execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
        log_event("subject_deleted", status=302, subject_id=subject_id)
        flash(f"Matière « {subject['name']} » supprimée.", "success")
        return redirect(url_for("manage.subjects"))
    return render_template(
        "confirm_delete.html",
        title="Supprimer une matière",
        message="Cette action est définitive.",
        details=[f"Matière : {subject['name']}"],
        action=url_for("manage.delete_subject", subject_id=subject_id),
        cancel=url_for("manage.subjects"),
    )
