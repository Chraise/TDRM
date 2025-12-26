from crypt import methods

from flask import render_template

from app.admin import bp
from app.decorators import admin_required

@bp.route('/index', methods=['GET'])
@admin_required
def index():
    return render_template('admin/index.html')