from datetime import datetime, timezone
from app import db


class EscalationRule(db.Model):
    __tablename__ = 'escalation_rules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))  # NULL = all depts
    priority = db.Column(db.String(20))                                     # NULL = all priorities
    level = db.Column(db.Integer, nullable=False)                           # 1, 2, or 3
    sla_type = db.Column(db.String(20), nullable=False, default='resolution')  # first_response / resolution
    breach_threshold_percent = db.Column(db.Integer, nullable=False, default=80)
    notify_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    department = db.relationship('Department', backref='escalation_rules')
    notify_user = db.relationship('User', backref='escalation_rules_to_notify')
    escalations = db.relationship('TicketEscalation', backref='rule')

    def __repr__(self):
        return f'<EscalationRule L{self.level} {self.name}>'


class TicketEscalation(db.Model):
    __tablename__ = 'ticket_escalations'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('escalation_rules.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    triggered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notified_at = db.Column(db.DateTime)

    ticket = db.relationship('Ticket', backref='escalations')

    __table_args__ = (
        db.UniqueConstraint('ticket_pk', 'rule_id', name='uq_ticket_escalation_rule'),
    )

    def __repr__(self):
        return f'<TicketEscalation ticket={self.ticket_pk} level={self.level}>'
