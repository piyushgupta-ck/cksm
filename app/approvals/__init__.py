from flask import Blueprint

bp = Blueprint('approvals', __name__)

from app.approvals import routes  # noqa: F401, E402
