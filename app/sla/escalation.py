"""
Escalation engine – check tickets against EscalationRules and fire alerts.
"""
from datetime import datetime, timezone
from app import db
from app.models.escalation import EscalationRule, TicketEscalation


def check_ticket_escalation(ticket, now=None):
    """
    For a given ticket, evaluate all active escalation rules.
    Creates a TicketEscalation record and sends a notification if the rule fires.
    De-duplicated: each (ticket, rule) pair can only escalate once.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    sla = ticket.sla
    if not sla:
        return

    # Find matching rules (department match or global, priority match or global)
    rules = EscalationRule.query.filter(
        db.or_(
            EscalationRule.department_id == ticket.department_id,
            EscalationRule.department_id.is_(None),
        ),
        db.or_(
            EscalationRule.priority == ticket.priority,
            EscalationRule.priority.is_(None),
        ),
        EscalationRule.is_active == True,
    ).all()

    for rule in rules:
        # Already escalated for this rule?
        already = TicketEscalation.query.filter_by(
            ticket_pk=ticket.id, rule_id=rule.id
        ).first()
        if already:
            continue

        # Determine which SLA deadline to evaluate
        if rule.sla_type == 'first_response':
            if sla.first_response_met:
                continue
            due = sla.first_response_due
        else:  # resolution
            if sla.resolution_met is not None:
                continue
            due = sla.resolution_due

        if not due:
            continue

        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        created_at = ticket.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        total_seconds = (due - created_at).total_seconds()
        if total_seconds <= 0:
            continue

        elapsed_seconds = (now - created_at).total_seconds()
        elapsed_pct = (elapsed_seconds / total_seconds) * 100

        if elapsed_pct < rule.breach_threshold_percent:
            continue

        # Fire!
        escalation = TicketEscalation(
            ticket_pk=ticket.id,
            rule_id=rule.id,
            level=rule.level,
            triggered_at=now,
            notified_at=now,
        )
        db.session.add(escalation)

        if rule.notify_user_id:
            try:
                from app.notifications.service import create_notification
                sla_label = rule.sla_type.replace('_', ' ').title()
                create_notification(
                    user_id=rule.notify_user_id,
                    notif_type='escalated',
                    title=f'SLA Escalation L{rule.level}: {ticket.ticket_id}',
                    message=(
                        f'Ticket {ticket.ticket_id} "{ticket.title}" has reached '
                        f'{rule.breach_threshold_percent}% of its {sla_label} SLA. '
                        f'Priority: {ticket.priority}.'
                    ),
                    ticket_pk=ticket.id,
                )
            except Exception:
                pass  # never break the SLA check loop
