from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from app.models import UserRole


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != required_role:
                flash('您没有权限访问该页面，请登录合适的账号。', 'warning')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required(UserRole.ADMIN)
stu_required = role_required(UserRole.STUDENT)
worker_required = role_required(UserRole.WORKER)