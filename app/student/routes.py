import os
import uuid

from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename
from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user
import sqlalchemy as sa

from app.student import bp
from app.student.forms import RepairOrderForm
from app.decorators import stu_required
from app import db
from app.models import RepairOrder, DormBuilding, OrderStatus, MaintenanceRecord


def allowed_file(filename, allowed_extensions=None):
    """检查文件扩展名是否允许"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'gif'})
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_uploaded_files(files):
    """
    保存上传的文件
    Returns:
        tuple: (db_string, physical_paths)
        - db_string: 数据库存储的相对路径字符串（逗号分隔），无文件则为 None
        - physical_paths: 磁盘绝对路径列表（用于异常回滚删除）
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
                relative_url = os.path.join('uploads', unique_filename).replace('\\', '/')
                saved_relative_urls.append(relative_url)
            except Exception as e:
                current_app.logger.error(f"无法保存文件 {filename}: {e}")

    db_string = ','.join(saved_relative_urls) if saved_relative_urls else None
    return db_string, saved_physical_paths


@bp.route('/')
@bp.route('/index')
@stu_required
def index():
    """学生首页"""
    return render_template('student/index.html')


@bp.route('/create_order', methods=['GET', 'POST'])
@stu_required
def create_order():
    """学生提交报修表单"""

    building_id = current_user.building.building_id
    building_name = current_user.building.building_name
    repair_location = current_user.room_no

    form = RepairOrderForm(
        building_id=building_id,
        building_name=building_name,
        repair_location=repair_location
    )

    if form.validate_on_submit():
        uploaded_physical_paths = []  # 用于异常回滚时删除文件

        try:
            # 处理图片上传
            image_urls_str = None
            if form.image_urls.data:
                valid_files = [f for f in form.image_urls.data if f.filename]
                if valid_files:
                    image_urls_str, uploaded_physical_paths = save_uploaded_files(valid_files)

            # 创建报修单
            repair_order = RepairOrder(
                submitter_id=current_user.user_id,
                repair_building_id=form.repair_building_id.data,
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
            # 异常回滚：数据库回滚 + 删除已上传文件
            db.session.rollback()
            current_app.logger.error(f'报修单提交失败: {str(e)}')

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
    """我的工单：显示当前学生提交的所有报修工单列表"""
    page = request.args.get('page', 1, type=int)
    status_param = request.args.get('status')

    query = RepairOrder.query.filter_by(submitter_id=current_user.user_id)
    query = query.options(
        selectinload(RepairOrder.maintenance_records).joinedload(MaintenanceRecord.worker)
    )

    # 假设前端传来的 status 就是 Enum 的成员名 (如 'Pending', 'Finished')
    if status_param and hasattr(OrderStatus, status_param):
        query = query.filter(RepairOrder.status == OrderStatus[status_param])

    pagination = query.order_by(RepairOrder.submit_time.desc()).paginate(
        page=page,
        per_page=current_app.config.get('POSTS_PER_PAGE', 10),
        error_out=False
    )

    return render_template('student/my_orders.html',
                           pagination=pagination,
                           current_status=status_param or 'all')  # 传回给前端用于高亮Tab