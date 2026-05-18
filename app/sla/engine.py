"""
SLA Engine – deadline computation, pause/resume, breach detection.
"""
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Policy lookup
# ---------------------------------------------------------------------------

def get_sla_policy(ticket):
    """
    Return the most specific active SLAPolicy for this ticket.
    Resolution order (most specific first):
      1. dept + priority
      2. dept only (priority IS NULL)
      3. global + priority (dept IS NULL)
      4. global default (both NULL)
    """
    from app.models.sla import SLAPolicy

    for dept_id, priority in [
        (ticket.department_id, ticket.priority),
        (ticket.department_id, None),
        (None, ticket.priority),
        (None, None),
    ]:
        policy = SLAPolicy.query.filter_by(
            department_id=dept_id,
            priority=priority,
            is_active=True,
        ).first()
        if policy:
            return policy
    return None


# ---------------------------------------------------------------------------
# Business hours helpers
# ---------------------------------------------------------------------------

def _get_business_hours():
    """Return {day_of_week: (start_time, end_time)} for working days."""
    from app.models.sla import BusinessHoursConfig
    result = {}
    for cfg in BusinessHoursConfig.query.all():
        if cfg.is_working_day:
            result[cfg.day_of_week] = (cfg.start_time, cfg.end_time)
    return result


def _get_holiday_dates():
    """Return a set of date objects for active holidays."""
    from app.models.sla import Holiday
    return {h.date for h in Holiday.query.filter_by(is_active=True).all()}


def add_business_hours(start_dt, hours, biz_hours=None, holiday_dates=None):
    """
    Return the datetime that is `hours` business-hours after `start_dt`.

    If biz_hours is None (no config), falls back to 24/7 calendar hours.
    """
    if not biz_hours:
        return start_dt + timedelta(hours=hours)

    if holiday_dates is None:
        holiday_dates = set()

    remaining = hours * 3600  # convert to seconds
    current = start_dt
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    # Safety: iterate at most 366 days worth of minutes
    for _ in range(366 * 1440):
        if remaining <= 0:
            break

        dow = current.weekday()          # 0=Mon … 6=Sun
        cur_date = current.date()

        if dow not in biz_hours or cur_date in holiday_dates:
            # Non-working day – skip to midnight of next day
            next_day = cur_date + timedelta(days=1)
            current = datetime(next_day.year, next_day.month, next_day.day,
                               0, 0, 0, tzinfo=timezone.utc)
            continue

        start_t, end_t = biz_hours[dow]
        day_start = datetime(cur_date.year, cur_date.month, cur_date.day,
                             start_t.hour, start_t.minute, 0, tzinfo=timezone.utc)
        day_end = datetime(cur_date.year, cur_date.month, cur_date.day,
                           end_t.hour, end_t.minute, 0, tzinfo=timezone.utc)

        if current < day_start:
            current = day_start

        if current >= day_end:
            # Past working hours today – move to next day
            next_day = cur_date + timedelta(days=1)
            current = datetime(next_day.year, next_day.month, next_day.day,
                               0, 0, 0, tzinfo=timezone.utc)
            continue

        available = (day_end - current).total_seconds()
        if remaining <= available:
            current += timedelta(seconds=remaining)
            remaining = 0
        else:
            remaining -= available
            next_day = cur_date + timedelta(days=1)
            current = datetime(next_day.year, next_day.month, next_day.day,
                               0, 0, 0, tzinfo=timezone.utc)

    return current


# ---------------------------------------------------------------------------
# SLA initialisation
# ---------------------------------------------------------------------------

def initialize_ticket_sla(ticket):
    """
    Create and attach a TicketSLA record to *ticket*.
    Caller must db.session.flush() before calling so ticket.id is set.
    """
    from app import db
    from app.models.sla import TicketSLA

    if ticket.sla:
        return ticket.sla

    policy = get_sla_policy(ticket)
    if not policy:
        return None

    created_at = ticket.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if policy.use_business_hours:
        biz_hours = _get_business_hours()
        holiday_dates = _get_holiday_dates()
    else:
        biz_hours = None
        holiday_dates = None

    fr_due = add_business_hours(created_at, policy.first_response_hours, biz_hours, holiday_dates)
    res_due = add_business_hours(created_at, policy.resolution_hours, biz_hours, holiday_dates)

    sla = TicketSLA(
        ticket_pk=ticket.id,
        policy_id=policy.id,
        first_response_due=fr_due,
        resolution_due=res_due,
    )
    db.session.add(sla)
    db.session.flush()   # so sla.id is available immediately
    return sla


# ---------------------------------------------------------------------------
# First-response
# ---------------------------------------------------------------------------

def mark_first_response(ticket, response_at=None):
    """Mark first-response SLA as met (idempotent)."""
    sla = ticket.sla
    if not sla or sla.first_response_met:
        return

    if response_at is None:
        response_at = datetime.now(timezone.utc)

    sla.first_response_met = True
    sla.first_response_at = response_at

    if sla.first_response_due:
        due = sla.first_response_due
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if response_at.tzinfo is None:
            response_at = response_at.replace(tzinfo=timezone.utc)
        sla.first_response_breached = response_at > due


# ---------------------------------------------------------------------------
# Pause / Resume
# ---------------------------------------------------------------------------

def pause_sla(ticket, reason='Hold'):
    """Pause SLA clock (idempotent)."""
    from app import db
    from app.models.sla import SLAPause

    sla = ticket.sla
    if not sla or sla.is_paused:
        return

    now = datetime.now(timezone.utc)
    sla.is_paused = True
    sla.pause_started_at = now

    pause = SLAPause(
        ticket_sla_id=sla.id,
        pause_reason=reason,
        paused_at=now,
    )
    db.session.add(pause)


def resume_sla(ticket):
    """Resume SLA clock and extend due-dates by the paused duration (idempotent)."""
    from app import db
    from app.models.sla import SLAPause

    sla = ticket.sla
    if not sla or not sla.is_paused:
        return

    now = datetime.now(timezone.utc)
    pause_start = sla.pause_started_at
    if pause_start and pause_start.tzinfo is None:
        pause_start = pause_start.replace(tzinfo=timezone.utc)

    paused_seconds = int((now - pause_start).total_seconds()) if pause_start else 0
    sla.total_paused_seconds = (sla.total_paused_seconds or 0) + paused_seconds

    offset = timedelta(seconds=paused_seconds)

    if sla.first_response_due and not sla.first_response_met:
        fr = sla.first_response_due
        if fr.tzinfo is None:
            fr = fr.replace(tzinfo=timezone.utc)
        sla.first_response_due = fr + offset

    if sla.resolution_due:
        rd = sla.resolution_due
        if rd.tzinfo is None:
            rd = rd.replace(tzinfo=timezone.utc)
        sla.resolution_due = rd + offset

    # Close open pause record
    last_pause = SLAPause.query.filter_by(
        ticket_sla_id=sla.id, resumed_at=None
    ).order_by(SLAPause.paused_at.desc()).first()
    if last_pause:
        last_pause.resumed_at = now
        last_pause.paused_seconds = paused_seconds

    sla.is_paused = False
    sla.pause_started_at = None


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def mark_resolution(ticket, resolved_at=None):
    """Record resolution outcome on the SLA record."""
    sla = ticket.sla
    if not sla:
        return

    if resolved_at is None:
        resolved_at = datetime.now(timezone.utc)

    if sla.is_paused:
        resume_sla(ticket)

    sla.resolved_at = resolved_at

    if sla.resolution_due:
        due = sla.resolution_due
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if resolved_at.tzinfo is None:
            resolved_at = resolved_at.replace(tzinfo=timezone.utc)
        sla.resolution_met = resolved_at <= due
        sla.resolution_breached = resolved_at > due
    else:
        sla.resolution_met = True
        sla.resolution_breached = False


# ---------------------------------------------------------------------------
# Batch breach check (called manually from admin or periodic task)
# ---------------------------------------------------------------------------

def check_sla_breaches(app):
    """
    Iterate all open tickets with SLA, update breach flags, fire escalations.
    Safe to call repeatedly – escalations are de-duplicated.
    """
    from app import db
    from app.models.ticket import Ticket
    from app.models.sla import TicketSLA
    from app.sla.escalation import check_ticket_escalation

    with app.app_context():
        now = datetime.now(timezone.utc)
        open_statuses = ['Open', 'InProgress', 'Hold', 'Reopened']

        tickets = (
            db.session.query(Ticket)
            .join(TicketSLA, TicketSLA.ticket_pk == Ticket.id)
            .filter(Ticket.status.in_(open_statuses))
            .all()
        )

        for ticket in tickets:
            sla = ticket.sla
            if sla.is_paused:
                continue

            # Update breach flags
            sla.compute_breach_status()

            # Check escalation rules
            check_ticket_escalation(ticket, now)

        db.session.commit()
