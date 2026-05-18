"""
Background scheduler — runs periodic tasks using APScheduler.

Starts automatically when the Flask app is created (unless
SCHEDULER_ENABLED = False in config).

Jobs:
  sla_check      — calls check_sla_breaches() every SLA_CHECK_INTERVAL_MINUTES (default 5)
  email_ingest   — polls IMAP mailbox every IMAP_POLL_INTERVAL_MINUTES (default 5)
                   only active when IMAP_ENABLED=true
"""
from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = None


def start_scheduler(app):
    global _scheduler

    if not app.config.get('SCHEDULER_ENABLED', True):
        app.logger.info('Scheduler disabled by SCHEDULER_ENABLED=False.')
        return

    if _scheduler and _scheduler.running:
        return  # already started (e.g. Flask debug reloader)

    _scheduler = BackgroundScheduler(daemon=True)

    # ── SLA breach check ─────────────────────────────────────────────────────
    sla_interval = app.config.get('SLA_CHECK_INTERVAL_MINUTES', 5)

    def _run_sla_check():
        try:
            from app.sla.engine import check_sla_breaches
            check_sla_breaches(app)
        except Exception as exc:
            app.logger.error('Scheduled SLA check failed: %s', exc)

    _scheduler.add_job(
        _run_sla_check,
        trigger='interval',
        minutes=sla_interval,
        id='sla_check',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # ── Email-to-Ticket ingest ────────────────────────────────────────────────
    if app.config.get('IMAP_ENABLED', False):
        email_interval = app.config.get('IMAP_POLL_INTERVAL_MINUTES', 5)

        def _run_email_ingest():
            try:
                from app.email_ingest.processor import process_emails
                process_emails(app)
            except Exception as exc:
                app.logger.error('Scheduled email ingest failed: %s', exc)

        _scheduler.add_job(
            _run_email_ingest,
            trigger='interval',
            minutes=email_interval,
            id='email_ingest',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        app.logger.info(
            'Email ingest scheduled — polling every %d min.', email_interval
        )

    _scheduler.start()
    app.logger.info(
        'Background scheduler started — SLA check every %d min.', sla_interval
    )


def shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
