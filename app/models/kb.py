import re
from datetime import datetime, timezone
from app import db


class KBCategory(db.Model):
    __tablename__ = 'kb_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    articles = db.relationship('KBArticle', backref='category', lazy='dynamic')

    @staticmethod
    def make_slug(name):
        slug = name.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        return slug.strip('-')

    def __repr__(self):
        return f'<KBCategory {self.name}>'


class KBArticle(db.Model):
    __tablename__ = 'kb_articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('kb_categories.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    tags = db.Column(db.String(500))          # comma-separated
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    author = db.relationship('User', backref='kb_articles')

    def get_tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    @staticmethod
    def make_slug(title):
        slug = title.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        return slug.strip('-')

    def __repr__(self):
        return f'<KBArticle {self.title}>'
