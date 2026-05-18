"""
Priority Rule models — admin-defined rule-based ticket priority assignment.

Logic
-----
- Rules are evaluated in ``priority_order`` order (lower integer = first).
- A rule fires when **ANY** of its condition-groups matches the ticket.
- Within a group, **ALL** conditions must match (AND).
- First matching rule sets the ticket priority; further rules are skipped.
"""
from datetime import datetime
from app import db

PRIORITY_VALUES = ['Low', 'Medium', 'High', 'Critical']

PRIORITY_COLORS = {
    'Low':      ('bg-green-100',  'text-green-800'),
    'Medium':   ('bg-yellow-100', 'text-yellow-800'),
    'High':     ('bg-orange-100', 'text-orange-800'),
    'Critical': ('bg-red-100',    'text-red-800'),
}


class PriorityRule(db.Model):
    """Top-level rule — owns condition groups and maps to a priority value."""
    __tablename__ = 'priority_rules'

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    description     = db.Column(db.Text, nullable=True)
    # Lower number = evaluated first when multiple rules are active
    priority_order  = db.Column(db.Integer, default=0, nullable=False, index=True)
    # The priority value this rule sets (Low / Medium / High / Critical)
    set_priority    = db.Column(db.String(20), nullable=False, default='Medium')
    is_active       = db.Column(db.Boolean, default=True, nullable=False)
    stop_on_match   = db.Column(db.Boolean, default=True, nullable=False)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow,
                                onupdate=datetime.utcnow, nullable=False)

    condition_groups = db.relationship(
        'PriorityRuleGroup',
        backref='rule',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='PriorityRuleGroup.group_order',
    )

    @property
    def total_conditions(self):
        total = 0
        for group in self.condition_groups:
            total += group.conditions.count()
        return total

    def __repr__(self):
        return f'<PriorityRule {self.id} {self.name!r} → {self.set_priority}>'


class PriorityRuleGroup(db.Model):
    """
    One condition-group inside a PriorityRule.
    Groups are OR-ed; within a group all conditions are AND-ed.
    """
    __tablename__ = 'priority_rule_groups'

    id          = db.Column(db.Integer, primary_key=True)
    rule_id     = db.Column(db.Integer,
                            db.ForeignKey('priority_rules.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    group_order = db.Column(db.Integer, default=0, nullable=False)

    conditions = db.relationship(
        'PriorityRuleCondition',
        backref='group',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='PriorityRuleCondition.condition_order',
    )

    def __repr__(self):
        return f'<PriorityRuleGroup {self.id} rule={self.rule_id}>'


class PriorityRuleCondition(db.Model):
    """
    A single field-level condition within a PriorityRuleGroup.
    Identical structure to AssignmentRuleCondition.
    """
    __tablename__ = 'priority_rule_conditions'

    id              = db.Column(db.Integer, primary_key=True)
    group_id        = db.Column(db.Integer,
                                db.ForeignKey('priority_rule_groups.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    field           = db.Column(db.String(50), nullable=False)
    operator        = db.Column(db.String(20), default='is', nullable=False)
    value_id        = db.Column(db.Integer, nullable=True)
    value_str       = db.Column(db.String(100), nullable=True)
    condition_order = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<PriorityRuleCondition {self.id} {self.field} {self.operator}>'
