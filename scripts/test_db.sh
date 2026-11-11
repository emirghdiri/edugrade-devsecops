#!/usr/bin/env bash
# Base PostgreSQL jetable pour les tests (port 5433 de l'hôte).
# Usage : scripts/test_db.sh start|stop|url
set -euo pipefail

NAME=edugrade-test-db
PORT="${TEST_DB_PORT:-5433}"
USER_=edugrade
DB=edugrade_test
PASS=edugrade-test   # valeur factice, base de test locale uniquement

case "${1:-}" in
  start)
    if ! docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
      docker rm -f "$NAME" >/dev/null 2>&1 || true
      docker run -d --name "$NAME" -p "127.0.0.1:$PORT:5432" \
        -e POSTGRES_USER="$USER_" -e POSTGRES_PASSWORD="$PASS" -e POSTGRES_DB="$DB" \
        postgres:16-alpine >/dev/null
    fi
    for _ in $(seq 1 30); do
      docker exec "$NAME" pg_isready -U "$USER_" -d "$DB" >/dev/null 2>&1 && { echo "base de test prête sur 127.0.0.1:$PORT"; exit 0; }
      sleep 1
    done
    echo "la base de test ne répond pas" >&2; exit 1 ;;
  stop)
    docker rm -f "$NAME" >/dev/null 2>&1 && echo "base de test supprimée" ;;
  url)
    echo "postgresql://$USER_:$PASS@127.0.0.1:$PORT/$DB" ;;
  *)
    echo "usage: $0 start|stop|url" >&2; exit 2 ;;
esac
