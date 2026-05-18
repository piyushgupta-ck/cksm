from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional


class CreateTicketForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('', '— Auto (let rules decide) —'),
        ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Critical', 'Critical')
    ], default='')
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    problem_id = SelectField('Problem', coerce=int, validators=[Optional()])
    sub_problem_id = SelectField('Sub-Problem', coerce=int, validators=[Optional()])
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    sub_category_id = SelectField('Sub-Category', coerce=int, validators=[Optional()])
    on_behalf_of = SelectField('On Behalf Of', coerce=int, validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    attachments = MultipleFileField('Attachments')
    submit = SubmitField('Create Ticket')


class TicketReplyForm(FlaskForm):
    content = TextAreaField('Reply', validators=[DataRequired()])
    is_internal = BooleanField('Internal Note')
    attachments = MultipleFileField('Attachments')
    submit = SubmitField('Send Reply')


class TicketStatusForm(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()])
    remarks = TextAreaField('Remarks', validators=[Optional()])
    submit = SubmitField('Update Status')


class TicketAssignForm(FlaskForm):
    assigned_to = SelectField('Assign To', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign')
