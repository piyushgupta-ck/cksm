from datetime import datetime, timezone
from app import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)
    # Types: ticket_created, assigned, replied, status_changed,
    #        escalated, approval_requested, approval_resolved, sla_breach
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'))
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship('User', backref='notifications')
    ticket = db.relationship('Ticket', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.type} user={self.user_id} read={self.is_read}>'
