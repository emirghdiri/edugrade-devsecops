"""Journaux applicatifs JSON sur la sortie standard.

Chaque ligne est un objet JSON contenant au minimum : timestamp, level, event,
user_id, role, route, ip, status. Ne jamais y placer de mot de passe, de secret
ni de valeur de note.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

from flask import has_request_context, request, session

LOGGER_NAME = "edugrade"
BASE_FIELDS = ("event", "user_id", "role", "route", "ip", "status")

# Motifs typiques d'injection SQL / XSS recherchés dans les saisies libres.
SUSPICIOUS_PATTERNS: dict[str, re.Pattern[str]] = {
    "quote": re.compile(r"'"),
    "sql_comment": re.compile(r"--"),
    "union": re.compile(r"\bunion\b", re.IGNORECASE),
    "script_tag": re.compile(r"<\s*script", re.IGNORECASE),
}

logger = logging.getLogger(LOGGER_NAME)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
        }
        fields = getattr(record, "fields", None)
        if fields:
            for key in BASE_FIELDS:
                payload[key] = fields.get(key)
            payload.update({k: v for k, v in fields.items() if k not in BASE_FIELDS})
        else:
            payload["event"] = "log"
            payload["message"] = record.getMessage()
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    # Les journaux d'accès de Werkzeug feraient doublon avec l'événement http_request.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def log_event(event: str, status: int | None = None, level: int = logging.INFO, **extra: Any) -> None:
    fields: dict[str, Any] = {"event": event, "status": status}
    if has_request_context():
        fields.update(
            user_id=session.get("user_id"),
            role=session.get("role"),
            route=request.path,
            ip=request.remote_addr,
            method=request.method,
        )
    fields.update(extra)
    logger.log(level, event, extra={"fields": fields})


def detect_suspicious(value: str) -> list[str]:
    return [name for name, pattern in SUSPICIOUS_PATTERNS.items() if pattern.search(value)]
