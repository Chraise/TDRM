"""
学生视图
"""
from flask import render_template
from flask_login import login_required
from . import bp


@bp.route('/')
@bp.route('/index')
@login_required
def index():
    """学生首页"""
    return render_template('student/index.html', title='学生首页')

