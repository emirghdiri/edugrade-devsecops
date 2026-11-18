#!/bin/sh
# Prépare la base (schéma + données de démonstration si elle est vide), puis
# remplace le shell par la commande du conteneur (Gunicorn par défaut).
set -e
python -m app.seed
exec "$@"
