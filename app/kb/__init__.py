from flask import Blueprint

bp = Blueprint('kb', __name__)

from app.kb import routes  # noqa
