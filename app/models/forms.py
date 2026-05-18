import json
from datetime import datetime, timezone
from app import db


class FormTemplate(db.Model):
    __tablename__ = 'form_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    department = db.relationship('Department', backref='form_templates')
    problem = db.relationship('Problem', backref='form_templates')
    fields = db.relationship('FormField', backref='template', lazy='dynamic',
                             order_by='FormField.order')

    def get_active_fields(self):
        return self.fields.filter_by(is_active=True).all()

    def __repr__(self):
        return f'<FormTemplate {self.name}>'


class FormField(db.Model):
    __tablename__ = 'form_fields'

    FIELD_TYPES = ['text', 'textarea', 'number', 'date', 'dropdown', 'checkbox', 'multiselect']

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('form_templates.id'), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)   # machine-safe name
    field_type = db.Column(db.String(20), nullable=False, default='text')
    options = db.Column(db.Text)      # JSON array for dropdown / multiselect
    placeholder = db.Column(db.String(200))
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def get_options_list(self):
        """Return options as a Python list (for dropdown / multiselect)."""
        if self.options:
            try:
                return json.loads(self.options)
            except (ValueError, TypeError):
                return []
        return []

    def __repr__(self):
        return f'<FormField {self.label}>'


class TicketFieldValue(db.Model):
    __tablename__ = 'ticket_field_values'

    id = db.Column(db.Integer, primary_key=True)
    ticket_pk = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    field_id = db.Column(db.Integer, db.ForeignKey('form_fields.id'), nullable=False)
    value = db.Column(db.Text)

    ticket = db.relationship('Ticket', backref='custom_field_values')
    field = db.relationship('FormField', backref='values')

    __table_args__ = (
        db.UniqueConstraint('ticket_pk', 'field_id', name='uq_ticket_field'),
    )

    def __repr__(self):
        return f'<TicketFieldValue ticket={self.ticket_pk} field={self.field_id}>'
