from flask import Blueprint

bp = Blueprint('worker', __name__)

from app.worker import routes
