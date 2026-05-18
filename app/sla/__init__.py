from flask import Blueprint

bp = Blueprint('sla', __name__)

from app.sla import routes  # noqa: F401, E402
