from datetime import datetime, timezone
from app import db


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    problems = db.relationship('Problem', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.name}>'


class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sub_problems = db.relationship('SubProblem', backref='problem', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('name', 'department_id', name='uq_problem_dept'),
    )

    def __repr__(self):
        return f'<Problem {self.name}>'


class SubProblem(db.Model):
    __tablename__ = 'sub_problems'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problems.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    categories = db.relationship('Category', backref='sub_problem', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('name', 'problem_id', name='uq_subproblem_problem'),
    )

    def __repr__(self):
        return f'<SubProblem {self.name}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    sub_problem_id = db.Column(db.Integer, db.ForeignKey('sub_problems.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sub_categories = db.relationship('SubCategory', backref='category', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('name', 'sub_problem_id', name='uq_category_subproblem'),
    )

    def __repr__(self):
        return f'<Category {self.name}>'


class SubCategory(db.Model):
    __tablename__ = 'sub_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('name', 'category_id', name='uq_subcategory_category'),
    )

    def __repr__(self):
        return f'<SubCategory {self.name}>'
