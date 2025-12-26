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