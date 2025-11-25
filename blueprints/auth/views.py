from flask import Blueprint
from . import bp  # 从 __init__.py 导入蓝图


@bp.route('/login')
def login():
    """登录页面"""
    return "登录"


@bp.route('/users')
def register():
    """用户列表"""
    return "用户列表"
