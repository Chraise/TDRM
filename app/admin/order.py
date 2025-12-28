from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from sqlalchemy import select, or_, func, case, String, cast, and_
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.admin import bp
from app.admin.forms import DispatchForm
from app.decorators import admin_required
from app.models import RepairOrder, User, OrderStatus, UserRole, DormBuilding, order_assign, MaintenanceRecord


@bp.route('/orders')
@admin_required
def order_list():
    """工单列表：支持状态筛选、搜索、智能排序"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filter_type = request.args.get('filter', 'active')
    search_query = request.args.get('q', '').strip()

    stmt = select(RepairOrder).options(
        joinedload(RepairOrder.submitter),
        joinedload(RepairOrder.building),
        selectinload(RepairOrder.assigned_workers)
    )

    if search_query:
        stmt = stmt.join(User, RepairOrder.submitter_id == User.user_id)\
                   .outerjoin(DormBuilding, RepairOrder.repair_building_id == DormBuilding.building_id)

    if filter_type == 'active':
        stmt = stmt.where(
            or_(
                RepairOrder.status == OrderStatus.PENDING,
                RepairOrder.status == OrderStatus.ASSIGNED,
                RepairOrder.status == OrderStatus.IN_PROGRESS
            )
        )

    if search_query:
        search_filter = or_(
            RepairOrder.title.ilike(f'%{search_query}%'),
            cast(RepairOrder.order_id, String).ilike(f'%{search_query}%'),
            User.username.ilike(f'%{search_query}%'),
            DormBuilding.building_name.ilike(f'%{search_query}%')
        )
        stmt = stmt.where(search_filter)

    # 状态权重排序：Pending > Assigned > InProgress > Completed > Cancelled
    status_weight = case(
        (RepairOrder.status == OrderStatus.PENDING, 1),
        (RepairOrder.status == OrderStatus.ASSIGNED, 2),
        (RepairOrder.status == OrderStatus.IN_PROGRESS, 3),
        (RepairOrder.status == OrderStatus.COMPLETED, 4),
        (RepairOrder.status == OrderStatus.CANCELLED, 5),
        else_=6
    )

    if filter_type == 'active':
        # 活跃工单：优先处理最早提交的（FIFO）
        stmt = stmt.order_by(
            status_weight.asc(),
            RepairOrder.submit_time.asc()
        )
    else:
        # 历史工单：按最新显示
        stmt = stmt.order_by(
            status_weight.asc(),
            RepairOrder.submit_time.desc()
        )

    orders = db.session.execute(stmt).scalars().unique().all()

    dispatch_form = DispatchForm()

    return render_template(
        'admin/order/list.html',
        orders=orders,
        dispatch_form=dispatch_form,
        current_filter=filter_type,
        OrderStatus=OrderStatus,
        posts_per_page=10
    )


@bp.route('/orders/dispatch/<int:order_id>', methods=['POST'])
@admin_required
def dispatch_order(order_id):
    """派单：支持多选维修工"""
    order = db.session.get(RepairOrder, order_id)
    if not order:
        flash('未找到该工单', 'danger')
        return redirect(url_for('admin.order_list'))

    form = DispatchForm()

    if form.validate_on_submit():
        worker_ids = form.worker_ids.data

        stmt = select(User).where(User.user_id.in_(worker_ids))
        workers = db.session.execute(stmt).scalars().all()

        if not workers:
            flash('选择的维修工无效', 'danger')
            return redirect(url_for('admin.order_list'))

        try:
            # 直接覆盖旧指派（如需追加可使用 extend）
            order.assigned_workers = workers

            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.ASSIGNED

            db.session.commit()

            names = ", ".join([w.username for w in workers])
            flash(f'工单 #{order.order_id} 已成功指派给: {names}', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'派单失败：数据库错误 {str(e)}', 'danger')
    else:
        flash(f'派单失败：{form.errors}', 'warning')

    return redirect(url_for('admin.order_list'))


@bp.route('/api/recommend-worker')
@admin_required
def recommend_worker():
    """推荐最空闲的维修工：统计活跃工单数最少者"""
    stmt = (
        select(
            User.user_id,
            User.username,
            User.account,
            func.count(RepairOrder.order_id).label('workload')
        )
        .select_from(User)
        .outerjoin(order_assign, User.user_id == order_assign.c.user_id)
        .outerjoin(
            RepairOrder,
            and_(
                order_assign.c.order_id == RepairOrder.order_id,
                RepairOrder.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS])
            )
        )
        .where(User.role == UserRole.WORKER, User.status == 1)
        .group_by(User.user_id, User.username, User.account)
        .order_by(func.count(RepairOrder.order_id).asc(), User.user_id.asc())
        .limit(1)
    )

    result = db.session.execute(stmt).first()

    if not result:
        return jsonify({'success': False, 'message': '暂无可用维修工'})

    best_worker = {
        'id': result.user_id,
        'name': result.username,
        'account': result.account,
        'count': result.workload or 0
    }

    return jsonify({
        'success': True,
        'data': best_worker,
        'message': f"推荐：{best_worker['name']} (当前积压: {best_worker['count']}单)"
    })


@bp.route('/orders/detail/<int:order_id>', methods=['GET'])
@admin_required
def order_detail(order_id):
    """工单详情：管理员查看报修信息和维修进度"""
    stmt = (
        select(RepairOrder)
        .where(RepairOrder.order_id == order_id)
        .options(
            joinedload(RepairOrder.building),
            joinedload(RepairOrder.submitter).joinedload(User.building),
            selectinload(RepairOrder.assigned_workers),
            selectinload(RepairOrder.maintenance_records)
            .joinedload(MaintenanceRecord.worker)
        )
    )
    order = db.session.execute(stmt).scalar_one_or_none()

    if not order:
        abort(404, description="工单不存在")

    # 对维修记录按时间排序
    if order.maintenance_records:
        order.maintenance_records.sort(key=lambda x: x.end_time or x.start_time, reverse=True)

    return render_template(
        'admin/order/detail.html',
        order=order
    )