"""
Gunicorn configuration for CKSM production deployment.

Local / Nginx:
    gunicorn -c gunicorn.conf.py wsgi:application

Railway / any PaaS:
    Set PORT env var (Railway does this automatically).
    Set GUNICORN_WORKERS=1 if IMAP_ENABLED=true (prevents duplicate scheduler jobs).
"""
import multiprocessing
import os

# ── Binding ───────────────────────────────────────────────────────────────────
# Railway injects PORT automatically; fall back to GUNICORN_BIND or 8000.
_port = os.environ.get('PORT')
if _port:
    bind = f'0.0.0.0:{_port}'
else:
    bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')

# ── Workers ───────────────────────────────────────────────────────────────────
# Cap at 4 to stay within Railway / small-VPS RAM limits.
# IMPORTANT: set GUNICORN_WORKERS=1 when IMAP_ENABLED=true to avoid
# APScheduler running duplicate email-ingest jobs across workers.
_default_workers = min(multiprocessing.cpu_count() * 2 + 1, 4)
workers = int(os.environ.get('GUNICORN_WORKERS', _default_workers))
worker_class = 'sync'
threads = 1
timeout = 120
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────────────────
# '-' sends logs to stdout/stderr so Railway / Docker capture them.
# Override with a file path (e.g. logs/access.log) for self-hosted setups.
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', '-')
errorlog  = os.environ.get('GUNICORN_ERROR_LOG',  '-')
loglevel  = os.environ.get('GUNICORN_LOG_LEVEL',  'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# ── Process name ─────────────────────────────────────────────────────────────
proc_name = 'cksm'

# ── Security ─────────────────────────────────────────────────────────────────
limit_request_line   = 4096
limit_request_fields = 100

# ── Hooks ────────────────────────────────────────────────────────────────────
def on_starting(server):
    # Create logs/ dir only when file logging is configured
    for path in [accesslog, errorlog]:
        if path and path != '-':
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else 'logs',
                        exist_ok=True)
