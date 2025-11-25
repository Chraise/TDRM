from flask import Blueprint

bp = Blueprint('worker', __name__)

from . import views