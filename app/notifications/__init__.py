from flask import Blueprint

bp = Blueprint('notifications', __name__)

from app.notifications import routes  # noqa: F401, E402
