"""
Assignment Rule Engine
======================
Evaluates active AssignmentRule records against a Ticket and returns the
User that should be assigned, or None if no rule matches.

Evaluation order
----------------
1. Rules sorted by ``priority`` ASC, then ``id`` ASC (stable tie-break).
2. A rule matches when **ANY** of its condition-groups matches.
3. A group matches when **ALL** of its conditions match.
4. The first matching rule wins — its ``assigned_agent`` is returned.

This mirrors Zoho-style "rule sets with OR-groups and AND-conditions".
"""
import logging

log = logging.getLogger(__name__)


def evaluate_assignment_rules(ticket):
    """
    Return the User assigned by the first matching rule, or ``None``.

    Parameters
    ----------
    ticket : app.models.ticket.Ticket
        Must already have department_id / problem_id / etc. set
        (call after ``db.session.flush()`` so FKs are populated).
    """
    from app.models.assignment_rule import AssignmentRule

    rules = (
        AssignmentRule.query
        .filter_by(is_active=True)
        .order_by(AssignmentRule.priority.asc(), AssignmentRule.id.asc())
        .all()
    )

    for rule in rules:
        if _rule_matches(ticket, rule):
            agent = rule.assigned_agent
            if not agent or not agent.is_active:
                log.warning(
                    'Assignment rule %r (id=%s) matched but agent is missing or inactive — skipping',
                    rule.name, rule.id,
                )
                continue  # try next rule
            log.debug(
                'Assignment rule %r (id=%s) matched ticket %s → agent %s',
                rule.name, rule.id, getattr(ticket, 'ticket_id', ticket.id),
                agent.full_name,
            )
            return agent

    log.debug('No assignment rule matched ticket %s',
              getattr(ticket, 'ticket_id', ticket.id))
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rule_matches(ticket, rule):
    """True when ANY condition-group of the rule matches."""
    groups = list(rule.condition_groups.order_by(None).all())
    if not groups:
        return False                  # rule with no groups never fires
    return any(_group_matches(ticket, g) for g in groups)


def _group_matches(ticket, group):
    """True when ALL conditions in the group match (empty group = wildcard)."""
    conditions = list(group.conditions.order_by(None).all())
    if not conditions:
        return True                   # empty group = always matches
    return all(_condition_matches(ticket, c) for c in conditions)


def _condition_matches(ticket, cond):
    """Evaluate a single condition against the ticket's field values."""
    _field_map = {
        'department':   ticket.department_id,
        'problem':      ticket.problem_id,
        'sub_problem':  ticket.sub_problem_id,
        'category':     ticket.category_id,
        'sub_category': ticket.sub_category_id,
        'priority':     ticket.priority,      # string field
    }

    ticket_value = _field_map.get(cond.field)

    # Resolve the condition's expected value
    if cond.field == 'priority':
        cond_value = cond.value_str            # e.g. "High"
    else:
        cond_value = cond.value_id             # integer FK

    if cond.operator == 'is':
        return ticket_value == cond_value
    if cond.operator == 'is_not':
        return ticket_value != cond_value

    log.warning('Unknown assignment rule operator %r — treating as no-match', cond.operator)
    return False
