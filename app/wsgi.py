"""Point d'entrée WSGI pour Gunicorn : gunicorn app.wsgi:app"""

from app import create_app

app = create_app()
