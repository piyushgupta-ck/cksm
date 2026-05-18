"""
Assignment Rule models — Zoho-style dynamic ticket routing.

Logic
-----
- Rules are evaluated in ``priority`` order (lower integer = first).
- A rule fires when **ANY** of its condition-groups matches the ticket.
- Within a group, **ALL** conditions must match (AND).
- First matching rule wins; further rules are skipped by default.
"""
from datetime import datetime
from app import db


# ---------------------------------------------------------------------------
# Lookup constants (kept here so templates/engine import from one place)
# ---------------------------------------------------------------------------

CONDITION_FIELDS = [
    ('department',   'Department'),
    ('problem',      'Problem'),
    ('sub_problem',  'Sub-Problem'),
    ('category',     'Category'),
    ('sub_category', 'Sub-Category'),
    ('priority',     'Priority'),
]

CONDITION_OPERATORS = [
    ('is',     'is'),
    ('is_not', 'is not'),
]

PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical']


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AssignmentRule(db.Model):
    """Top-level rule — owns condition groups and points to an agent."""
    __tablename__ = 'assignment_rules'

    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(200), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    # Lower number = evaluated first when multiple rules are active
    priority       = db.Column(db.Integer, default=0, nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active      = db.Column(db.Boolean, default=True, nullable=False)
    # When True, no further rules are evaluated after this one matches
    stop_on_match  = db.Column(db.Boolean, default=True, nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow,
                               onupdate=datetime.utcnow, nullable=False)

    condition_groups = db.relationship(
        'AssignmentRuleGroup',
        backref='rule',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='AssignmentRuleGroup.group_order',
    )
    assigned_agent = db.relationship('User', foreign_keys=[assigned_to_id])

    @property
    def total_conditions(self):
        """Quick count of all conditions across all groups (for list display)."""
        total = 0
        for group in self.condition_groups:
            total += group.conditions.count()
        return total

    def __repr__(self):
        return f'<AssignmentRule {self.id} {self.name!r}>'


class AssignmentRuleGroup(db.Model):
    """
    One condition-group inside an AssignmentRule.

    Groups are OR-ed: if ANY group matches the ticket the rule fires.
    Within a group all conditions are AND-ed.
    """
    __tablename__ = 'assignment_rule_groups'

    id          = db.Column(db.Integer, primary_key=True)
    rule_id     = db.Column(db.Integer,
                            db.ForeignKey('assignment_rules.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    group_order = db.Column(db.Integer, default=0, nullable=False)

    conditions = db.relationship(
        'AssignmentRuleCondition',
        backref='group',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='AssignmentRuleCondition.condition_order',
    )

    def __repr__(self):
        return f'<AssignmentRuleGroup {self.id} rule={self.rule_id}>'


class AssignmentRuleCondition(db.Model):
    """
    A single field-level condition within an AssignmentRuleGroup.

    - Entity fields  (department, problem, sub_problem, category, sub_category):
        ``value_id``  = the PK of the entity,  ``value_str`` is NULL.
    - Enum fields (priority):
        ``value_str`` = the string value (e.g. "High"),  ``value_id`` is NULL.
    """
    __tablename__ = 'assignment_rule_conditions'

    id              = db.Column(db.Integer, primary_key=True)
    group_id        = db.Column(db.Integer,
                                db.ForeignKey('assignment_rule_groups.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    field           = db.Column(db.String(50), nullable=False)
    operator        = db.Column(db.String(20), default='is', nullable=False)
    value_id        = db.Column(db.Integer, nullable=True)
    value_str       = db.Column(db.String(100), nullable=True)
    condition_order = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<AssignmentRuleCondition {self.id} {self.field} {self.operator}>'
