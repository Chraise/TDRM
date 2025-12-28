import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename
from flask import render_template, flash, redirect, url_for, request, current_app, abort
from flask_login import current_user
from sqlalchemy import select, case

from app.student import bp
from app.student.forms import RepairOrderForm, RateOrderForm
from app.decorators import stu_required
from app import db
from app.models import RepairOrder, DormBuilding, OrderStatus, MaintenanceRecord

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def allowed_file(filename, allowed_extensions=None):
    """验证文件扩展名是否在允许列表中"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'gif'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_files(files):
    """
    保存上传的图片文件，返回数据库路径和物理路径
    返回: (db_string, physical_paths)
    - db_string: 逗号分隔的相对路径字符串，用于数据库存储
    - physical_paths: 绝对路径列表，用于异常回滚时删除文件
    """
    if not files:
        return None, []

    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)

    saved_relative_urls = []
    saved_physical_paths = []

    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(upload_folder, unique_filename)

            try:
                file.save(file_path)
                saved_physical_paths.append(file_path)
                relative_url = f"uploads/{unique_filename}"
                saved_relative_urls.append(relative_url)
            except Exception as e:
                current_app.logger.error(f"无法保存文件 {filename}: {e}")

    db_string = ','.join(saved_relative_urls) if saved_relative_urls else None
    return db_string, saved_physical_paths


@bp.route('/')
@bp.route('/index')
@stu_required
def index():
    """学生端首页"""
    return render_template('student/index.html')


@bp.route('/create_order', methods=['GET', 'POST'])
@stu_required
def create_order():
    """发起报修：处理工单提交与图片上传"""
    if not current_user.building:
        flash('您的账户未关联宿舍楼，无法提交报修单', 'danger')
        return redirect(url_for('student.index'))
    
    building_id = current_user.building.building_id
    building_name = current_user.building.building_name
    repair_location = current_user.room_no or ''

    form = RepairOrderForm()
    
    if request.method == 'GET':
        form.repair_building_id.data = building_id
        form.building_name.data = building_name
        form.repair_location.data = repair_location

    if form.validate_on_submit():
        uploaded_physical_paths = []

        try:
            image_urls_str = None
            if form.image_urls.data:
                valid_files = [f for f in form.image_urls.data if f.filename]
                if valid_files:
                    image_urls_str, uploaded_physical_paths = save_uploaded_files(valid_files)

            # 安全策略：直接从用户信息获取 building_id，不信任表单数据
            repair_order = RepairOrder(
                submitter_id=current_user.user_id,
                repair_building_id=building_id,
                repair_location=form.repair_location.data,
                title=form.title.data,
                description=form.description.data if form.description.data else None,
                image_urls=image_urls_str,
                status=OrderStatus.PENDING
            )

            db.session.add(repair_order)
            db.session.commit()

            flash('报修单提交成功！', 'success')
            return redirect(url_for('student.index'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'报修单提交失败: {str(e)}')

            # 异常回滚：删除已上传的文件
            if uploaded_physical_paths:
                for path in uploaded_physical_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                            current_app.logger.info(f"回滚文件: {path}")
                    except OSError as cleanup_error:
                        current_app.logger.error(f"回滚文件过程中，删除失败: {cleanup_error}")

            flash(f'提交失败，请重试。错误信息：{str(e)}', 'danger')

    return render_template('student/create_order.html', form=form)


@bp.route('/my_orders', methods=['GET'])
@stu_required
def my_orders():
    """我的工单：支持按状态筛选和智能排序"""
    status_param = request.args.get('status')

    stmt = (
        select(RepairOrder)
        .where(RepairOrder.submitter_id == current_user.user_id)
        .options(
            selectinload(RepairOrder.maintenance_records).joinedload(MaintenanceRecord.worker)
        )
    )

    if status_param and hasattr(OrderStatus, status_param):
        stmt = stmt.where(RepairOrder.status == OrderStatus[status_param])

    # 状态权重排序：Pending > Assigned > InProgress > Completed > Cancelled
    status_weight = case(
        (RepairOrder.status == OrderStatus.PENDING, 1),
        (RepairOrder.status == OrderStatus.ASSIGNED, 2),
        (RepairOrder.status == OrderStatus.IN_PROGRESS, 3),
        (RepairOrder.status == OrderStatus.COMPLETED, 4),
        (RepairOrder.status == OrderStatus.CANCELLED, 5),
        else_=6
    )

    stmt = stmt.order_by(
        status_weight.asc(),
        RepairOrder.submit_time.desc()
    )
    
    orders = db.session.execute(stmt).scalars().all()

    return render_template('student/my_orders.html',
                           orders=orders,
                           current_status=status_param or 'all',
                           posts_per_page=current_app.config.get('POSTS_PER_PAGE', 10))


@bp.route('/order/detail/<int:order_id>', methods=['GET'])
@stu_required
def order_detail(order_id):
    """工单详情：查看报修信息和维修进度"""
    stmt = (
        select(RepairOrder)
        .where(RepairOrder.order_id == order_id)
        .options(
            joinedload(RepairOrder.building),
            selectinload(RepairOrder.assigned_workers),
            selectinload(RepairOrder.maintenance_records)
            .joinedload(MaintenanceRecord.worker)
        )
    )
    order = db.session.execute(stmt).scalar_one_or_none()

    if not order:
        abort(404, description="工单不存在")
    # 权限校验：仅允许查看自己的工单
    if order.submitter_id != current_user.user_id:
        abort(403, description="您没有权限查看此工单")

    if order.maintenance_records:
        order.maintenance_records.sort(key=lambda x: x.end_time or x.start_time, reverse=True)

    # 只有已完成且未评价的工单才能进行评价
    can_rate = (order.status == OrderStatus.COMPLETED) and (order.rating is None)

    return render_template(
        'student/order_detail.html',
        order=order,
        can_rate=can_rate
    )


@bp.route('/order/cancel/<int:order_id>', methods=['POST'])
@stu_required
def cancel_order(order_id):
    """取消工单：仅允许取消待处理状态的工单"""
    order = db.session.get(RepairOrder, order_id)

    # 权限校验：确保只能操作自己的工单
    if not order or order.submitter_id != current_user.user_id:
        flash('无权操作此工单', 'danger')
        return redirect(url_for('student.my_orders'))
    # 业务规则：只有待处理状态的工单才能取消
    if not order.is_pending:
        flash('工单已处理或已完成，无法取消', 'warning')
        return redirect(url_for('student.order_detail', order_id=order_id))

    order.status = OrderStatus.CANCELLED
    db.session.commit()
    flash('工单已成功取消', 'success')

    return redirect(url_for('student.order_detail', order_id=order_id))


@bp.route('/order/rate/<int:order_id>', methods=['GET', 'POST'])
@stu_required
def rate_order(order_id):
    """评价工单：仅允许对已完成且未评价的工单进行评价"""
    order = db.session.get(RepairOrder, order_id)

    # 权限校验：确保只能操作自己的工单
    if not order or order.submitter_id != current_user.user_id:
        flash('无法访问该工单', 'danger')
        return redirect(url_for('student.my_orders'))
    # 业务规则：只有已完成状态的工单才能评价
    if order.status != OrderStatus.COMPLETED:
        flash('工单尚未完成，无法评价', 'warning')
        return redirect(url_for('student.order_detail', order_id=order_id))
    # 防止重复评价
    if order.rating is not None:
        flash('您已经评价过该工单', 'info')
        return redirect(url_for('student.order_detail', order_id=order_id))

    form = RateOrderForm()

    if form.validate_on_submit():
        try:
            order.rating = form.rating.data
            order.feedback = form.feedback.data
            db.session.commit()

            flash('感谢您的评价！', 'success')
            return redirect(url_for('student.order_detail', order_id=order_id))
        except Exception as e:
            db.session.rollback()
            flash(f'评价提交失败: {str(e)}', 'danger')

    return render_template('student/rate_order.html', form=form, order=order)