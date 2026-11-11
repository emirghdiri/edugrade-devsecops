"""Application factory EduGrade."""

from __future__ import annotations

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db, security
from .config import Config, build_database_url
from .logging_setup import configure_logging, log_event


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.config["DATABASE_URL"] = build_database_url(app.config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY doit être définie (variable d'environnement).")

    configure_logging(app.config["LOG_LEVEL"])

    # Nginx est le seul proxy devant l'application : on lui fait confiance
    # pour l'IP cliente et le schéma d'origine.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    security.init_app(app)

    from . import auth, student, teacher

    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(teacher.bp)

    @app.get("/healthz")
    def healthz():
        ok = db.ping()
        return {"status": "ok" if ok else "degraded", "database": "ok" if ok else "unreachable"}, 200 if ok else 503

    _register_error_handlers(app)
    _register_request_log(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    messages = {
        400: "Requête invalide.",
        403: "Accès refusé.",
        404: "Page introuvable.",
        500: "Erreur interne.",
    }

    def handler(err):
        code = getattr(err, "code", 500) or 500
        return render_template("errors/error.html", code=code, message=messages.get(code, "Erreur.")), code

    for code in messages:
        app.register_error_handler(code, handler)


def _register_request_log(app: Flask) -> None:
    @app.after_request
    def log_request(response):
        if not request.path.startswith("/static") and request.path != "/healthz":
            log_event("http_request", status=response.status_code)
        return response
