from functools import wraps
from flask import abort
from flask_login import current_user
from app.models import UserRole

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 必须先登录，且角色必须是 ADMIN
        if not current_user.is_authenticated or current_user.role != UserRole.ADMIN:
            abort(403) # 抛出禁止访问异常
        return f(*args, **kwargs)
    return decorated_function

def stu_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 必须先登录，且角色必须是 STU
        if not current_user.is_authenticated or current_user.role != UserRole.STUDENT:
            abort(403) # 抛出禁止访问异常
        return f(*args, **kwargs)
    return decorated_function

def worker_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 必须先登录，且角色必须是 WORKER
        if not current_user.is_authenticated or current_user.role != UserRole.WORKER:
            abort(403) # 抛出禁止访问异常
        return f(*args, **kwargs)
    return decorated_function