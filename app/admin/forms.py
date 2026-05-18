from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class CreateUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    submit = SubmitField('Create User')


class EditUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    role_id = SelectField('Role', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User')


class DepartmentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class ProblemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class SubProblemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    problem_id = SelectField('Problem', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    sub_problem_id = SelectField('Sub Problem', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')


class SubCategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=120)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')
