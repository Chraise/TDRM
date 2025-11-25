"""
维修人员视图
"""
from flask import render_template
from flask_login import login_required
from . import bp


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """维修人员首页"""
    return render_template('worker/index.html', title='维修人员首页')

