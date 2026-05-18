"""
Token-based authentication helper for the REST API.

Usage on protected routes:
    @bp.route('/some-endpoint')
    @api_token_required
    def some_endpoint():
        ...
        g.api_user   ← the authenticated User

Clients send:
    Authorization: Bearer <token>
"""
from functools import wraps
from datetime import datetime, timezone
from flask import request, jsonify, g
from app.models.api_token import APIToken


def api_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header.'}), 401

        plain_token = auth_header[7:].strip()   # strip "Bearer "

        # Find token by prefix (first 8 chars) for faster lookup
        prefix = plain_token[:8]
        candidates = APIToken.query.filter_by(prefix=prefix, is_active=True).all()

        token_obj = None
        for t in candidates:
            if t.verify(plain_token):
                token_obj = t
                break

        if not token_obj:
            return jsonify({'error': 'Invalid or revoked API token.'}), 401

        if not token_obj.user.is_active:
            return jsonify({'error': 'User account is disabled.'}), 403

        # Update last_used_at
        token_obj.last_used_at = datetime.now(timezone.utc)
        from app import db
        db.session.commit()

        g.api_user = token_obj.user
        g.api_token = token_obj
        return f(*args, **kwargs)
    return decorated
