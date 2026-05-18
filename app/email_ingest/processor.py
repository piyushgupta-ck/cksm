"""
Email-to-Ticket Processor
=========================
Uses Python's built-in imaplib + email to poll an IMAP mailbox and
create CKSM tickets from unread emails.

Config keys (all read from Flask app.config / .env):
    IMAP_ENABLED       true/false  (default false)
    IMAP_SERVER        e.g. imap.gmail.com
    IMAP_PORT          993
    IMAP_USE_SSL       true
    IMAP_USERNAME      mailbox@company.com
    IMAP_PASSWORD      app-password
    IMAP_FOLDER        INBOX
    IMAP_DEFAULT_DEPT  department name to assign if sender not in a dept (default 'IT')
    IMAP_DEFAULT_PRIORITY  Medium
"""

import imaplib
import email
import email.header
import re
from email.utils import parseaddr


def _decode_header(value):
    """Decode RFC 2047 encoded email header to a plain string."""
    if not value:
        return ''
    parts = []
    for decoded, charset in email.header.decode_header(value):
        if isinstance(decoded, bytes):
            try:
                parts.append(decoded.decode(charset or 'utf-8', errors='replace'))
            except (LookupError, UnicodeDecodeError):
                parts.append(decoded.decode('utf-8', errors='replace'))
        else:
            parts.append(decoded)
    return ''.join(parts)


def _get_body(msg):
    """Extract plain-text body from an email.message.Message."""
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get('Content-Disposition', ''))
            if ct == 'text/plain' and 'attachment' not in disp:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                except Exception:
                    pass
                break
    else:
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
        except Exception:
            body = str(msg.get_payload())
    return body.strip()


def process_emails(app):
    """
    Main entry point called by the scheduler.
    Opens an IMAP connection, fetches UNSEEN emails, creates tickets,
    marks them as SEEN.
    """
    with app.app_context():
        cfg = app.config

        if not cfg.get('IMAP_ENABLED', False):
            return

        server = cfg.get('IMAP_SERVER')
        port = int(cfg.get('IMAP_PORT', 993))
        use_ssl = cfg.get('IMAP_USE_SSL', True)
        username = cfg.get('IMAP_USERNAME')
        password = cfg.get('IMAP_PASSWORD')
        folder = cfg.get('IMAP_FOLDER', 'INBOX')
        default_dept_name = cfg.get('IMAP_DEFAULT_DEPT', 'IT')
        default_priority = cfg.get('IMAP_DEFAULT_PRIORITY', 'Medium')

        if not (server and username and password):
            app.logger.warning('Email ingest: IMAP credentials not configured.')
            return

        try:
            if use_ssl:
                conn = imaplib.IMAP4_SSL(server, port)
            else:
                conn = imaplib.IMAP4(server, port)
            conn.login(username, password)
        except Exception as exc:
            app.logger.error('Email ingest: IMAP login failed: %s', exc)
            return

        try:
            conn.select(folder)
            status, data = conn.search(None, 'UNSEEN')
            if status != 'OK' or not data or not data[0]:
                return

            uids = data[0].split()
            app.logger.info('Email ingest: found %d unread email(s).', len(uids))

            from app import db
            from app.models.user import User, Role
            from app.models.department import Department
            from app.models.ticket import Ticket, TicketActivityLog

            for uid in uids:
                try:
                    _process_single_email(
                        conn, uid, app,
                        default_dept_name, default_priority,
                    )
                except Exception as exc:
                    app.logger.error(
                        'Email ingest: error processing uid %s: %s', uid, exc
                    )

        finally:
            try:
                conn.logout()
            except Exception:
                pass


def _process_single_email(conn, uid, app, default_dept_name, default_priority):
    """Fetch one email, create a ticket, mark as SEEN."""
    from app import db
    from app.models.user import User, Role
    from app.models.department import Department
    from app.models.ticket import Ticket, TicketActivityLog
    from app.sla.engine import attach_sla

    _, msg_data = conn.fetch(uid, '(RFC822)')
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)

    subject = _decode_header(msg.get('Subject', '')) or '(No Subject)'
    from_raw = msg.get('From', '')
    _, from_email = parseaddr(from_raw)
    from_email = from_email.lower().strip()

    body = _get_body(msg)
    if not body:
        body = subject  # fallback

    # Limit lengths
    title = subject[:255]
    description = body[:10000]

    # Look up sender
    sender_user = User.query.filter(
        User.email.ilike(from_email), User.is_active == True
    ).first()

    if not sender_user:
        # Fall back to first active admin
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            sender_user = User.query.filter_by(
                role_id=admin_role.id, is_active=True
            ).first()

    if not sender_user:
        app.logger.warning(
            'Email ingest: cannot map sender %s to any user, skipping.', from_email
        )
        return

    # Find default department
    dept = (Department.query
            .filter(Department.name.ilike(default_dept_name), Department.is_active == True)
            .first())
    if not dept:
        dept = Department.query.filter_by(is_active=True).first()

    if not dept:
        app.logger.warning('Email ingest: no active department found, skipping.')
        return

    # Deduplicate: skip if a ticket from same sender+subject was created in last 5 min
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    duplicate = (Ticket.query
                 .filter(Ticket.created_by == sender_user.id,
                         Ticket.title == title,
                         Ticket.created_at >= cutoff)
                 .first())
    if duplicate:
        app.logger.info(
            'Email ingest: duplicate detected for "%s", skipping.', title
        )
        conn.store(uid, '+FLAGS', '\\Seen')
        return

    ticket_id = Ticket.generate_ticket_id()
    ticket = Ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        department_id=dept.id,
        priority=default_priority,
        created_by=sender_user.id,
    )
    db.session.add(ticket)
    db.session.flush()

    db.session.add(TicketActivityLog(
        ticket_pk=ticket.id,
        user_id=sender_user.id,
        action='created',
        details=f'Ticket auto-created from email by {from_email}',
    ))
    db.session.commit()

    try:
        attach_sla(ticket)
        db.session.commit()
    except Exception:
        pass

    # Mark email as SEEN
    conn.store(uid, '+FLAGS', '\\Seen')
    app.logger.info(
        'Email ingest: created ticket %s from %s — "%s"',
        ticket.ticket_id, from_email, title
    )
