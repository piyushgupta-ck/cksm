"""
Priority Rule Engine
====================
Evaluates active PriorityRule records against a Ticket and returns the
priority string that should be set, or None if no rule matches.

Evaluation order
----------------
1. Rules sorted by ``priority_order`` ASC, then ``id`` ASC (stable tie-break).
2. A rule matches when **ANY** of its condition-groups matches.
3. A group matches when **ALL** of its conditions match.
4. The first matching rule wins — its ``set_priority`` value is returned.
"""
import logging

log = logging.getLogger(__name__)

DEFAULT_PRIORITY = 'Medium'


def evaluate_priority_rules(ticket):
    """
    Return the priority string set by the first matching rule, or ``None``
    if no rule matches (caller should fall back to DEFAULT_PRIORITY).

    Parameters
    ----------
    ticket : app.models.ticket.Ticket
        Must already have department_id / problem_id / etc. set
        (call after ``db.session.flush()``).
    """
    from app.models.priority_rule import PriorityRule

    rules = (
        PriorityRule.query
        .filter_by(is_active=True)
        .order_by(PriorityRule.priority_order.asc(), PriorityRule.id.asc())
        .all()
    )

    for rule in rules:
        if _rule_matches(ticket, rule):
            log.debug(
                'Priority rule %r (id=%s) matched ticket %s → %s',
                rule.name, rule.id,
                getattr(ticket, 'ticket_id', ticket.id),
                rule.set_priority,
            )
            return rule.set_priority

    log.debug('No priority rule matched ticket %s — using default',
              getattr(ticket, 'ticket_id', ticket.id))
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rule_matches(ticket, rule):
    groups = list(rule.condition_groups.order_by(None).all())
    if not groups:
        return False
    return any(_group_matches(ticket, g) for g in groups)


def _group_matches(ticket, group):
    conditions = list(group.conditions.order_by(None).all())
    if not conditions:
        return True
    return all(_condition_matches(ticket, c) for c in conditions)


def _condition_matches(ticket, cond):
    _field_map = {
        'department':   ticket.department_id,
        'problem':      ticket.problem_id,
        'sub_problem':  ticket.sub_problem_id,
        'category':     ticket.category_id,
        'sub_category': ticket.sub_category_id,
        'priority':     ticket.priority,
    }

    ticket_value = _field_map.get(cond.field)
    cond_value   = cond.value_str if cond.field == 'priority' else cond.value_id

    if cond.operator == 'is':
        return ticket_value == cond_value
    if cond.operator == 'is_not':
        return ticket_value != cond_value

    log.warning('Unknown priority rule operator %r — treating as no-match', cond.operator)
    return False
