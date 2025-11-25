"""
管理员视图
"""
from flask import render_template
from flask_login import login_required
from . import bp


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """管理员首页"""
    return render_template('admin/index.html', title='管理员首页')

