from flask import Blueprint

bp = Blueprint('tickets', __name__, template_folder='../templates/tickets')

from app.tickets import routes
