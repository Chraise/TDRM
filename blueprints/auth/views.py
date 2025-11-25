"""
认证视图模块
处理用户登录、注册、登出等功能
"""
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User, DormBuilding, UserRole

# 从当前包的 __init__.py 导入蓝图
from . import bp


def get_redirect_url(user=None):
    """
    根据用户角色返回相应的首页URL
    
    参数:
        user: 用户对象，如果为None则使用current_user
    
    返回:
        对应角色的首页URL
    """
    if user is None:
        user = current_user
    
    if user.is_admin:
        return url_for('admin.index')
    elif user.is_student:
        return url_for('student.index')
    elif user.is_worker:
        return url_for('worker.index')
    else:
        return url_for('index')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    用户登录
    
    GET: 显示登录表单
    POST: 处理登录请求
    """
    # 如果用户已登录，重定向到对应角色的首页
    if current_user.is_authenticated:
        return redirect(get_redirect_url())
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        # 验证输入
        if not username or not password:
            flash('请输入用户名和密码', 'error')
            return render_template('auth/login.html')
        
        # 查询用户
        user = User.query.filter_by(username=username).first()
        
        # 验证用户
        if user is None:
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html')
        
        # 检查用户状态
        if not user.is_active_user:
            flash('该账号已被禁用，请联系管理员', 'error')
            return render_template('auth/login.html')
        
        # 验证密码
        if not user.check_password(password):
            flash('用户名或密码错误', 'error')
            return render_template('auth/login.html')
        
        # 登录成功
        login_user(user, remember=remember)
        flash(f'欢迎回来，{user.username}！', 'success')
        
        # 重定向到对应角色的首页
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(get_redirect_url(user))
    
    # GET 请求，显示登录表单
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户注册
    
    GET: 显示注册表单
    POST: 处理注册请求
    """
    # 如果用户已登录，重定向到对应角色的首页
    if current_user.is_authenticated:
        return redirect(get_redirect_url())
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        role = request.form.get('role', '').strip()
        contact = request.form.get('contact', '').strip()
        building_name = request.form.get('building_name', '').strip()
        room_no = request.form.get('room_no', '').strip()
        
        # 验证输入
        errors = []
        
        if not username:
            errors.append('请输入用户名')
        elif len(username) < 2 or len(username) > 50:
            errors.append('用户名长度应在2-50个字符之间')
        elif User.query.filter_by(username=username).first():
            errors.append('该用户名已被使用')
        
        if not password:
            errors.append('请输入密码')
        elif len(password) < 6:
            errors.append('密码长度至少为6个字符')
        elif password != password_confirm:
            errors.append('两次输入的密码不一致')
        
        if not role or role not in [UserRole.STUDENT, UserRole.WORKER]:
            errors.append('请选择注册角色（学生或维修人员）')
        
        if role == UserRole.STUDENT and not room_no:
            errors.append('学生必须填写房间号')
        
        # 如果有错误，显示错误信息
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html', 
                                 buildings=DormBuilding.query.all())
        
        # 查找或创建宿舍楼
        building = None
        if building_name:
            building = DormBuilding.query.filter_by(building_name=building_name).first()
            if not building:
                # 如果宿舍楼不存在，创建一个新的
                building = DormBuilding(
                    building_name=building_name,
                    location='',
                    admin_contact=''
                )
                db.session.add(building)
                db.session.flush()  # 获取building_id
        
        # 创建新用户
        user = User(
            username=username,
            role=role,
            contact=contact if contact else None,
            building_id=building.building_id if building else None,
            room_no=room_no if room_no else None,
            status=1
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}', 'error')
            return render_template('auth/register.html',
                                 buildings=DormBuilding.query.all())
    
    # GET 请求，显示注册表单
    buildings = DormBuilding.query.all()
    return render_template('auth/register.html', buildings=buildings)


@bp.route('/logout')
@login_required
def logout():
    """
    用户登出
    """
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('auth.login'))
