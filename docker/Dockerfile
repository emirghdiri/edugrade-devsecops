# syntax=docker/dockerfile:1

# ---------- Étape 1 : installation des dépendances dans un venv ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /tmp/requirements.txt


# ---------- Étape 2 : image d'exécution minimale ----------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="edugrade-backend" \
      org.opencontainers.image.description="EduGrade - backend Flask (projet pédagogique DevSecOps)" \
      org.opencontainers.image.source="https://github.com/emirghdiri/edugrade-devsecops"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Utilisateur applicatif sans privilège, UID/GID fixes (10001) pour pouvoir
# l'imposer côté Kubernetes (runAsUser) et dans les politiques Kyverno.
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app

WORKDIR /srv

# Seul le venv est repris de l'étape de build : pas de pip cache ni d'outil de compilation.
COPY --from=builder /opt/venv /opt/venv
# Le code appartient à root et n'est pas modifiable par l'utilisateur applicatif.
COPY app/ ./app/
COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# --no-control-socket : pas de socket d'administration (inutile, et le système de fichiers est en lecture seule).
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-tmp-dir", "/dev/shm", "--no-control-socket", "--forwarded-allow-ips", "*", "app.wsgi:app"]
