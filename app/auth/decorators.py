from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*role_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role.name not in role_names:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role.name != 'Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
