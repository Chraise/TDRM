from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length, Regexp


class LoginForm(FlaskForm):
    account = StringField('用户名（学号/工号）', validators=[
        DataRequired(message="请输入账号"),
        Length(min=4, max=20, message="账号长度应在 4 到 20 位之间"),
        Regexp(r'^\d+$', message="格式错误：账号必须为纯数字")
    ])
    password = PasswordField('密码', validators=[DataRequired(message="请输入密码")])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')


class ResetPasswordRequestForm(FlaskForm):
    """请求重置密码表单"""
    email = StringField('邮箱', validators=[DataRequired(message="请输入邮箱"), Email(message="邮箱格式不正确")])
    submit = SubmitField('发送重置邮件')


class ResetPasswordForm(FlaskForm):
    """重置密码表单"""
    password = PasswordField('新密码', validators=[DataRequired(message="请输入新密码")])
    confirm = PasswordField('确认密码', validators=[
        DataRequired(message="请确认密码"),
        EqualTo('password', message="两次输入的密码不一致")
    ])
    submit = SubmitField('重置密码')


class ChangePasswordForm(FlaskForm):
    """修改密码表单"""
    old_password = PasswordField('旧密码', validators=[DataRequired(message="请输入旧密码")])
    password = PasswordField('新密码', validators=[DataRequired(message="请输入新密码")])
    confirm = PasswordField('确认密码', validators=[
        DataRequired(message="请确认密码"),
        EqualTo('password', message="两次输入的密码不一致")
    ])
    submit = SubmitField('修改密码')