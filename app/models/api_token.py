import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class APIToken(db.Model):
    __tablename__ = 'api_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)       # descriptive label, e.g. "Mobile App"
    token_hash = db.Column(db.String(256), nullable=False, unique=True)
    prefix = db.Column(db.String(8), nullable=False)       # first 8 chars shown in UI for identification
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='api_tokens')

    @staticmethod
    def generate():
        """
        Create a new token.
        Returns (plain_token_string, APIToken_instance).
        Caller must set user_id + name before adding to session.
        """
        plain = secrets.token_urlsafe(32)
        instance = APIToken(
            token_hash=generate_password_hash(plain),
            prefix=plain[:8],
        )
        return plain, instance

    def verify(self, plain_token):
        return check_password_hash(self.token_hash, plain_token)

    def __repr__(self):
        return f'<APIToken {self.prefix}… name={self.name}>'
