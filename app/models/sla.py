from datetime import datetime, timezone
from app import db


class SLAPolicy(db.Model):
    __tablename__ = 'sla_policies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))  # NULL = applies to all
    priority = db.Column(db.String(20))                                     # NULL = applies to all
    first_response_hours = db.Column(db.Float, nullable=False, default=4.0)
    resolution_hours = db.Column(db.Float, nullable=False, default=24.0)
    use_business_hours = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    department = db.relationship('Department', backref='sla_policies')

    def __repr__(self):
        return f'<SLAPolicy {self.name}>'


class BusinessHoursConfig(db.Model):
    __tablename__ = 'business_hours'

    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False, unique=True)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_working_day = db.Column(db.Boolean, default=True, nullable=False)

    DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    @property
    def day_name(self):
        return self.DAY_NAMES[self.day_of_week]


class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class TicketSLA(db.Model):
    __tablename__ = 'ticket_sla'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), unique=True, nullable=False)
    policy_id = db.Column(db.Integer, db.ForeignKey('sla_policies.id'))

    first_response_due = db.Column(db.DateTime)
    resolution_due = db.Column(db.DateTime)

    first_response_met = db.Column(db.Boolean, default=False, nullable=False)
    first_response_at = db.Column(db.DateTime)
    first_response_breached = db.Column(db.Boolean, default=False, nullable=False)

    resolution_met = db.Column(db.Boolean)        # None = not yet resolved
    resolved_at = db.Column(db.DateTime)
    resolution_breached = db.Column(db.Boolean, default=False, nullable=False)

    # Pause tracking
    is_paused = db.Column(db.Boolean, default=False, nullable=False)
    pause_started_at = db.Column(db.DateTime)
    total_paused_seconds = db.Column(db.Integer, default=0, nullable=False)

    policy = db.relationship('SLAPolicy', backref='ticket_slas')
    ticket = db.relationship('Ticket', backref=db.backref('sla', uselist=False))
    pauses = db.relationship('SLAPause', backref='ticket_sla', lazy='dynamic')

    @property
    def is_first_response_due_soon(self):
        """True if first response is due within the next hour."""
        if self.first_response_met or not self.first_response_due:
            return False
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        due = self.first_response_due
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return now < due <= now + timedelta(hours=1)

    @property
    def is_resolution_due_soon(self):
        """True if resolution is due within the next 2 hours."""
        if self.resolution_met is not None or not self.resolution_due:
            return False
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        due = self.resolution_due
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        return now < due <= now + timedelta(hours=2)

    def compute_breach_status(self):
        """Re-evaluate breach flags based on current time."""
        now = datetime.now(timezone.utc)
        if not self.first_response_met and self.first_response_due:
            due = self.first_response_due
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            self.first_response_breached = now > due
        if self.resolution_met is None and self.resolution_due:
            due = self.resolution_due
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            self.resolution_breached = now > due

    def __repr__(self):
        return f'<TicketSLA ticket_pk={self.ticket_pk}>'


class SLAPause(db.Model):
    __tablename__ = 'sla_pauses'

    id = db.Column(db.Integer, primary_key=True)
    ticket_sla_id = db.Column(db.Integer, db.ForeignKey('ticket_sla.id'), nullable=False)
    pause_reason = db.Column(db.String(100))
    paused_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resumed_at = db.Column(db.DateTime)
    paused_seconds = db.Column(db.Integer)
