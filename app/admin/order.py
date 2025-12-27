from flask import render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import select, or_, func
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.admin import bp
from app.admin.forms import DispatchForm  # 确保 forms.py 中有 DispatchForm
from app.decorators import admin_required
from app.models import RepairOrder, User, OrderStatus, UserRole

from sqlalchemy import select, or_, case  # 记得导入 case


@bp.route('/orders')
@admin_required
def order_list():
    """
    管理员：工单列表页 (高性能优化版 + 智能排序)
    """
    page = request.args.get('page', 1, type=int)
    per_page = 10
    filter_type = request.args.get('filter', 'active')

    stmt = select(RepairOrder).options(
        joinedload(RepairOrder.submitter),
        joinedload(RepairOrder.building),
        selectinload(RepairOrder.assigned_workers)
    )

    # --- 筛选逻辑 ---
    if filter_type == 'active':
        stmt = stmt.where(
            or_(
                RepairOrder.status == OrderStatus.PENDING,
                RepairOrder.status == OrderStatus.ASSIGNED,
                RepairOrder.status == OrderStatus.IN_PROGRESS
            )
        )

    # --- 核心：智能排序逻辑 (Smart Ordering) ---
    # 1. 定义状态权重：Pending(1) > Assigned(2) > InProgress(3) > 其他(4)
    # 使用 case 语句将枚举转换为用于排序的整数权重
    status_weight = case(
        (RepairOrder.status == OrderStatus.PENDING, 1),
        (RepairOrder.status == OrderStatus.ASSIGNED, 2),
        (RepairOrder.status == OrderStatus.IN_PROGRESS, 3),
        (RepairOrder.status == OrderStatus.COMPLETED, 4),
        (RepairOrder.status == OrderStatus.CANCELLED, 5),
        else_=6
    )

    # 2. 应用组合排序
    # 第一关键字：按状态权重升序 (待处理排最前)
    # 第二关键字：按提交时间升序 (旧的单子排前面，优先解决积压问题)
    # 注意：如果是查看"全部历史"，完成的单子可能希望按时间倒序，这里做一个简单判断

    if filter_type == 'active':
        stmt = stmt.order_by(
            status_weight.asc(),  # 先看状态
            RepairOrder.submit_time.asc()  # 同状态下，优先处理最早提交的 (FIFO)
        )
    else:
        # 查看历史归档时，通常想看最近发生了什么，所以时间倒序
        stmt = stmt.order_by(
            status_weight.asc(),  # 依然保持未完成的在前面
            RepairOrder.submit_time.desc()  # 历史单子按最新显示
        )

    # --- 执行分页 ---
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)

    dispatch_form = DispatchForm()

    return render_template(
        'admin/order/list.html',
        orders=pagination.items,
        pagination=pagination,
        dispatch_form=dispatch_form,
        current_filter=filter_type,
        OrderStatus=OrderStatus
    )


@bp.route('/orders/dispatch/<int:order_id>', methods=['POST'])
@admin_required
def dispatch_order(order_id):
    """
    管理员：处理派单动作 (支持多选)
    """
    order = db.session.get(RepairOrder, order_id)
    if not order:
        flash('未找到该工单', 'danger')
        return redirect(url_for('admin.order_list'))

    form = DispatchForm()

    if form.validate_on_submit():
        # 1. 获取选中的 ID 列表 [1, 2, ...]
        worker_ids = form.worker_ids.data

        # 2. 批量查询这些 User 对象
        stmt = select(User).where(User.user_id.in_(worker_ids))
        workers = db.session.execute(stmt).scalars().all()

        if not workers:
            flash('选择的维修工无效', 'danger')
            return redirect(url_for('admin.order_list'))

        try:
            # 3. 更新多对多关系
            # 直接赋值会覆盖旧的列表（即：重置指派团队）
            # 如果你想在原有基础上增加，可以使用 order.assigned_workers.extend(workers)
            # 但通常派单操作是“指定当前负责人”，所以直接覆盖更符合直觉
            order.assigned_workers = workers

            # 4. 更新状态
            if order.status == OrderStatus.PENDING:
                order.status = OrderStatus.ASSIGNED

            # 如果已完成的工单被重新派单，可能需要考虑是否重置状态，这里暂时保持原逻辑

            db.session.commit()

            # 生成提示语：指派给 张三, 李四
            names = ", ".join([w.username for w in workers])
            flash(f'工单 #{order.order_id} 已成功指派给: {names}', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'派单失败：数据库错误 {str(e)}', 'danger')
    else:
        # 打印表单错误
        flash(f'派单失败：{form.errors}', 'warning')

    return redirect(url_for('admin.order_list'))


@bp.route('/api/recommend-worker')
@admin_required
def recommend_worker():
    """
    API: 获取当前工作量最少的维修师傅
    逻辑：统计每个维修工处于 Assigned 或 InProgress 状态的工单数量，取最小值。
    """
    # 1. 找出所有“维修中”或“已指派”的工单状态
    active_statuses = [OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS]

    # 2. 构建查询：获取所有维修工及其当前活跃工单数
    # 使用 outerjoin 确保即使没有工单的师傅也能被查出来 (count 为 0)
    stmt = (
        select(
            User.user_id,
            User.username,
            User.account,
            func.count(RepairOrder.order_id).label('workload')
        )
        .select_from(User)
        .outerjoin(User.assigned_orders)
        .where(User.role == UserRole.WORKER, User.status == 1)  # 仅限在职维修工
        # 核心技巧：在 join 条件或 where 中过滤工单状态。
        # 这里为了准确统计，我们需要过滤掉 'Completed' 和 'Cancelled' 的工单
        # 但要注意 outerjoin 的陷阱，如果在 where 里直接过滤 RepairOrder.status，会把 count=0 的人过滤掉
        # 所以这里的逻辑倾向于：先查人，再用子查询或 Python 处理，为了代码可读性，这里用 Python 处理（假设维修工数量不多）
    )

    # 方案 B (Python 处理，更稳健):
    # 先查出所有维修工，再查询他们的活跃工单数
    workers = db.session.execute(select(User).where(User.role == UserRole.WORKER, User.status == 1)).scalars().all()

    worker_stats = []
    for w in workers:
        # 计算该师傅手头的活跃工单 (不包含 Pending，因为 Pending 还没具体派给谁，或者看你业务逻辑)
        # 这里假设 logic 是：已派给他的(Assigned) + 他正在修的(InProgress)
        active_count = 0
        for order in w.assigned_orders:
            if order.status in active_statuses:
                active_count += 1

        worker_stats.append({
            'id': w.user_id,
            'name': w.username,
            'account': w.account,
            'count': active_count
        })

    if not worker_stats:
        return jsonify({'success': False, 'message': '暂无可用维修工'})

    # 3. 排序：按工单数升序，工单数相同时按 ID 随机或排序
    # key=lambda x: x['count'] 自动找最小的
    best_worker = min(worker_stats, key=lambda x: x['count'])

    return jsonify({
        'success': True,
        'data': best_worker,
        'message': f"推荐：{best_worker['name']} (当前积压: {best_worker['count']}单)"
    })