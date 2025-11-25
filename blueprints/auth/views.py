from flask import Blueprint

# 创建蓝图
auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    return "登录"


@auth.route('/users')
def register():
    return "用户列表"
