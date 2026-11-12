"""Connexion et déconnexion par session."""

from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import query_one
from .logging_setup import log_event

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("student.index"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = query_one("SELECT id, name, password_hash, role FROM users WHERE email = %s", (email,))

    if user is None or not check_password_hash(user["password_hash"], password):
        log_event("login_failed", status=401, level=logging.WARNING)
        flash("Identifiants invalides.", "error")
        return render_template("login.html", email=email), 401

    # Nouvelle session à chaque connexion (évite la fixation de session).
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    session["name"] = user["name"]
    log_event("login_success", status=302)
    # Toujours vers l'accueil interne : aucune URL de redirection n'est lue dans la requête.
    return redirect(url_for("student.index"))


@bp.route("/logout", methods=["POST"])
def logout():
    log_event("logout", status=302)
    session.clear()
    flash("Vous êtes déconnecté.", "info")
    return redirect(url_for("auth.login"))
