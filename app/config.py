import os
from dotenv import load_dotenv

load_dotenv()


def _bool(key, default='false'):
    return os.environ.get(key, default).lower() in ('1', 'true', 'yes')


class Config:
    # ── Core ─────────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # PostgreSQL in production:  postgresql://user:pass@host:5432/dbname
    # SQLite for development:    sqlite:///cksm.db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///cksm.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Recommended for PostgreSQL connections behind a load-balancer / proxy
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # ── Mail (outbound SMTP) ─────────────────────────────────────────────────
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = _bool('MAIL_USE_TLS', 'true')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@citykart.com')

    # ── Uploads ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/static/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))

    # ── Scheduler ────────────────────────────────────────────────────────────
    SCHEDULER_ENABLED = _bool('SCHEDULER_ENABLED', 'true')
    SLA_CHECK_INTERVAL_MINUTES = int(os.environ.get('SLA_CHECK_INTERVAL_MINUTES', 5))

    # ── Email-to-Ticket (IMAP ingest) ─────────────────────────────────────────
    IMAP_ENABLED = _bool('IMAP_ENABLED', 'false')
    IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.gmail.com')
    IMAP_PORT = int(os.environ.get('IMAP_PORT', 993))
    IMAP_USE_SSL = _bool('IMAP_USE_SSL', 'true')
    IMAP_USERNAME = os.environ.get('IMAP_USERNAME')
    IMAP_PASSWORD = os.environ.get('IMAP_PASSWORD')
    IMAP_FOLDER = os.environ.get('IMAP_FOLDER', 'INBOX')
    IMAP_POLL_INTERVAL_MINUTES = int(os.environ.get('IMAP_POLL_INTERVAL_MINUTES', 5))
    IMAP_DEFAULT_DEPT = os.environ.get('IMAP_DEFAULT_DEPT', 'IT')
    IMAP_DEFAULT_PRIORITY = os.environ.get('IMAP_DEFAULT_PRIORITY', 'Medium')

    # ── Testing flag (disables scheduler) ────────────────────────────────────
    TESTING = _bool('TESTING', 'false')
