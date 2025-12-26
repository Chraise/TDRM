from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm
from app import db
import sqlalchemy as sa

from app.models import User, UserRole

def get_redirect_url_by_role(user):
    if user.role == UserRole.ADMIN:
        return url_for('admin.index')
    elif user.role == UserRole.STUDENT:
        return url_for('student.index')
    elif user.role == UserRole.WORKER:
        return url_for('worker.index')
    else:
        logout_user()
        flash('登录失败：您的账户角色异常，请联系系统管理员。')
        return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        next_page = get_redirect_url_by_role(current_user)
        return redirect(next_page)
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.account == form.account.data)) # scalar 返回查询结果集中的第一个元素
        if user is None or not user.check_password(form.password.data):
            flash('用户不存在或密码错误')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)

        next_page = get_redirect_url_by_role(user)
        return redirect(next_page)

    return render_template('auth/login.html', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))