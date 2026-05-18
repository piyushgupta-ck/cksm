from datetime import datetime, timezone
from app import db


class ApprovalRequest(db.Model):
    __tablename__ = 'approval_requests'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # The specific person who must approve or reject this request
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.Text)
    requested_action = db.Column(db.String(50), nullable=False, default='Hold')
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    # status: pending, approved, rejected
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime)

    ticket = db.relationship('Ticket', backref='approval_requests')
    requester = db.relationship('User', foreign_keys=[requested_by], backref='approval_requests_made')
    approver  = db.relationship('User', foreign_keys=[approver_id],  backref='approvals_to_action')
    actions = db.relationship('ApprovalAction', backref='approval_request',
                              order_by='ApprovalAction.created_at')

    @property
    def is_pending(self):
        return self.status == 'pending'

    def __repr__(self):
        return f'<ApprovalRequest {self.id} status={self.status}>'


class ApprovalAction(db.Model):
    __tablename__ = 'approval_actions'

    id = db.Column(db.Integer, primary_key=True)
    approval_request_id = db.Column(db.Integer, db.ForeignKey('approval_requests.id'), nullable=False)
    actioned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # approved / rejected
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    actioner = db.relationship('User', backref='approval_actions_taken')


class ApprovalHistory(db.Model):
    __tablename__ = 'approval_history'

    id = db.Column(db.Integer, primary_key=True)
    approval_request_id = db.Column(db.Integer, db.ForeignKey('approval_requests.id'), nullable=False)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    approval_request = db.relationship('ApprovalRequest', backref='history')
    ticket = db.relationship('Ticket', backref='approval_history')
