from flask import render_template, flash, redirect, url_for, request
from urllib.parse import urlsplit
from flask_login import current_user, login_user, logout_user

from app.auth import bp
from app.auth.forms import LoginForm, ResetPasswordRequestForm, ResetPasswordForm
from app import db
import sqlalchemy as sa

from app.models import User, UserRole
from app.email import send_password_reset_email

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


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """请求重置密码"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
            flash('如果您的邮箱已注册，您将收到重置邮件', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('账户不存在，请联系管理员', 'error')
    return render_template('auth/reset_password_request.html', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """重置密码"""
    if current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('无效或已过期的重置链接')
        return redirect(url_for('auth.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('您的密码已成功重置')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)