"""Contrôles transverses : jeton anti-CSRF des formulaires et décorateurs d'accès."""

from __future__ import annotations

import hmac
import logging
import secrets
from functools import wraps
from typing import Callable

from flask import Flask, abort, redirect, request, session, url_for

from .logging_setup import log_event

CSRF_SESSION_KEY = "_csrf"
CSRF_FORM_FIELD = "csrf_token"


def csrf_token() -> str:
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def _check_csrf() -> None:
    if request.method != "POST":
        return
    expected = session.get(CSRF_SESSION_KEY, "")
    received = request.form.get(CSRF_FORM_FIELD, "")
    if not expected or not hmac.compare_digest(expected, received):
        log_event("csrf_failed", status=400, level=logging.WARNING)
        abort(400)


def init_app(app: Flask) -> None:
    app.before_request(_check_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def role_required(*roles: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                log_event("access_denied", status=403, level=logging.WARNING, reason="role", required_roles=list(roles))
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
