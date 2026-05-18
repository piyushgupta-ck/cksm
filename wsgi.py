"""
WSGI entry-point for Gunicorn / uWSGI production deployment.

Usage:
    gunicorn -c gunicorn.conf.py wsgi:application
"""
from app import create_app

application = create_app()

# Alias so Flask CLI (`flask run`) still works without extra config
app = application
