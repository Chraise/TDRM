from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import current_user
from sqlalchemy import select, or_, case
from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import User, UserRole
from app.admin.forms import UserCreateForm, UserEditForm, DeleteForm


@bp.route('/users')
@admin_required
def user_list():
    """
    用户列表页：支持分页、角色筛选、关键词搜索
    """
    page = request.args.get('page', 1, type=int)
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('q', '').strip()

    stmt = select(User)

    if role_filter == 'student':
        stmt = stmt.where(User.role == UserRole.STUDENT)
    elif role_filter == 'worker':
        stmt = stmt.where(User.role == UserRole.WORKER)
    elif role_filter == 'admin':
        stmt = stmt.where(User.role == UserRole.ADMIN)

    if search_query:
        stmt = stmt.where(
            or_(
                User.account.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%')
            )
        )

    # 排序：角色优先级（Admin > Worker > Student） > 状态（正常 > 禁用） > 账号（字母顺序）
    role_order = case(
        (User.role == UserRole.ADMIN, 1),
        (User.role == UserRole.WORKER, 2),
        (User.role == UserRole.STUDENT, 3),
        else_=4
    )
    stmt = stmt.order_by(
        role_order.asc(),      # 角色：Admin在前
        User.status.desc(),    # 状态：正常(1)在前，禁用(0)在后
        User.account.asc()     # 账号：字母顺序
    )

    pagination = db.paginate(stmt, page=page, per_page=current_app.config.get('USERS_PER_PAGE', 10), error_out=False)

    delete_form = DeleteForm()

    return render_template('admin/user/list.html',
                           users=pagination.items,
                           pagination=pagination,
                           current_filter=role_filter,
                           search_query=search_query,
                           delete_form=delete_form)


@bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def user_add():
    form = UserCreateForm()

    if form.validate_on_submit():
        try:
            role_enum = UserRole(form.role.data)
            password = form.password.data if form.password.data else '123456'

            new_user = User(
                account=form.account.data,
                username=form.username.data,
                email=form.email.data,
                role=role_enum,
                status=1
            )

            new_user.set_password(password)

            if role_enum == UserRole.STUDENT:
                new_user.building_id = form.building_id.data
                new_user.room_no = form.room_no.data

            db.session.add(new_user)
            db.session.commit()

            flash(f'用户 {new_user.username} 创建成功', 'success')
            return redirect(url_for('admin.user_list'))

        except ValueError as e:
            flash(f'参数错误: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'数据库错误: {str(e)}', 'danger')

    return render_template('admin/user/form.html', form=form, title="新增用户")


@bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def user_edit(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('用户不存在', 'danger')
        return redirect(url_for('admin.user_list'))

    form = UserEditForm(original_user_id=user.user_id, obj=user)

    if request.method == 'GET':
        form.role.data = user.role.value

    if form.validate_on_submit():
        try:
            form.populate_obj(user)
            user.role = UserRole(form.role.data)

            if user.role != UserRole.STUDENT:
                user.building_id = None
                user.room_no = None

            db.session.commit()
            flash(f'用户 {user.username} 信息已更新', 'success')
            return redirect(url_for('admin.user_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'更新失败: {str(e)}', 'danger')

    return render_template('admin/user/form.html', form=form, title="编辑用户")


@bp.route('/users/status/<int:user_id>', methods=['POST'])
@admin_required
def user_toggle_status(user_id):
    """
    切换用户状态：启用 <-> 禁用
    注意：防止管理员禁用自己
    """
    if user_id == current_user.user_id:
        flash('无法禁用当前登录的管理员账号', 'warning')
        return redirect(url_for('admin.user_list'))

    user = db.session.get(User, user_id)
    if user:
        user.status = 1 - user.status
        db.session.commit()

        status_msg = "已激活" if user.status == 1 else "已禁用"
        flash(f'用户 {user.username} {status_msg}', 'success')
    else:
        flash('用户不存在', 'danger')

    return redirect(url_for('admin.user_list'))


@bp.route('/users/reset-pwd/<int:user_id>', methods=['POST'])
@admin_required
def user_reset_pwd(user_id):
    """
    强制重置用户密码为默认值 (123456)
    """
    user = db.session.get(User, user_id)
    if user:
        user.set_password('123456')
        db.session.commit()
        flash(f'用户 {user.username} 的密码已重置为 "123456"', 'info')
    else:
        flash('用户不存在', 'danger')

    return redirect(url_for('admin.user_list'))