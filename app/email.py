"""
邮件发送辅助模块
"""
from threading import Thread
from flask import render_template, current_app, url_for
from flask_mail import Message
from app import mail


def send_async_email(app, msg):
    """异步发送邮件"""
    with app.app_context():
        mail.send(msg)


def send_password_reset_email(user):
    """发送密码重置邮件"""
    token = user.get_reset_password_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    msg = Message(
        '重置密码',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email]
    )

    msg.html = render_template('email/reset_password.html', user=user, token=token, reset_url=reset_url)
    msg.body = render_template('email/reset_password.txt', user=user, token=token, reset_url=reset_url)
    

    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()

