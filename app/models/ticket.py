from datetime import datetime, timezone
from app import db


class TicketSequence(db.Model):
    __tablename__ = 'ticket_sequences'

    year = db.Column(db.Integer, primary_key=True)
    last_number = db.Column(db.Integer, default=0, nullable=False)


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    status = db.Column(db.String(20), nullable=False, default='Open', index=True)
    priority = db.Column(db.String(20), nullable=False, default='Medium')

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'))
    sub_problem_id = db.Column(db.Integer, db.ForeignKey('sub_problems.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    sub_category_id = db.Column(db.Integer, db.ForeignKey('sub_categories.id'))

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_on_behalf_of = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    department = db.relationship('Department', backref='tickets')
    problem = db.relationship('Problem', backref='tickets')
    sub_problem = db.relationship('SubProblem', backref='tickets')
    category = db.relationship('Category', backref='tickets')
    sub_category = db.relationship('SubCategory', backref='tickets')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tickets')
    assignee = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_tickets')
    behalf_user = db.relationship('User', foreign_keys=[created_on_behalf_of])
    messages = db.relationship('TicketMessage', backref='ticket', lazy='dynamic',
                               order_by='TicketMessage.created_at')
    attachments = db.relationship('TicketAttachment', backref='ticket', lazy='dynamic')
    activity_logs = db.relationship('TicketActivityLog', backref='ticket', lazy='dynamic',
                                    order_by='TicketActivityLog.created_at.desc()')
    status_history = db.relationship('TicketStatusHistory', backref='ticket', lazy='dynamic',
                                     order_by='TicketStatusHistory.changed_at.desc()')

    STATUSES = ['Open', 'InProgress', 'Hold', 'Resolved', 'Rejected', 'Reopened', 'Closed']
    PRIORITIES = ['Low', 'Medium', 'High', 'Critical']

    @staticmethod
    def generate_ticket_id():
        year = datetime.now(timezone.utc).year
        seq = db.session.get(TicketSequence, year)
        if not seq:
            seq = TicketSequence(year=year, last_number=0)
            db.session.add(seq)
        seq.last_number += 1
        db.session.flush()
        return f'TKT-{year}-{seq.last_number:06d}'

    @property
    def effective_requester(self):
        if self.created_on_behalf_of:
            return self.behalf_user
        return self.creator

    def __repr__(self):
        return f'<Ticket {self.ticket_id}>'


class TicketMessage(db.Model):
    __tablename__ = 'ticket_messages'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='ticket_messages')

    def __repr__(self):
        return f'<TicketMessage {self.id} on Ticket {self.ticket_pk}>'


class TicketAttachment(db.Model):
    __tablename__ = 'ticket_attachments'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('ticket_messages.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='attachments')
    message = db.relationship('TicketMessage', backref='attachments')

    def __repr__(self):
        return f'<TicketAttachment {self.original_filename}>'


class TicketActivityLog(db.Model):
    __tablename__ = 'ticket_activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='activity_logs')

    def __repr__(self):
        return f'<TicketActivityLog {self.action}>'


class TicketStatusHistory(db.Model):
    __tablename__ = 'ticket_status_history'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    remarks = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='status_changes')

    def __repr__(self):
        return f'<StatusHistory {self.old_status} -> {self.new_status}>'
