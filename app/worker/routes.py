from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload, joinedload

from app import db
from app.worker import bp
from app.decorators import worker_required
from app.models import (
    RepairOrder, OrderStatus, MaintenanceRecord,
    SparePart, PartUsageDetail, User
)
from app.worker.forms import StartRepairForm, MaintenanceReportForm

HOURLY_RATE = 50.0
LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def local_today_range():
    """计算本地时区今天的起止时间（UTC）"""
    now_local = datetime.now(LOCAL_TZ)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_week_range():
    """计算本地时区本周的起止时间（UTC）"""
    now_local = datetime.now(LOCAL_TZ)
    days_since_monday = now_local.weekday()
    week_start_local = (now_local - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end_local = week_start_local + timedelta(days=7)
    return week_start_local.astimezone(timezone.utc), week_end_local.astimezone(timezone.utc)


def local_month_range():
    """计算本地时区本月的起止时间（UTC）"""
    now_local = datetime.now(LOCAL_TZ)
    month_start_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start_local.month == 12:
        month_end_local = month_start_local.replace(year=month_start_local.year + 1, month=1)
    else:
        month_end_local = month_start_local.replace(month=month_start_local.month + 1)
    return month_start_local.astimezone(timezone.utc), month_end_local.astimezone(timezone.utc)


def naive_to_utc(naive_dt):
    """将无时区的datetime视为本地时间，转换为UTC"""
    return naive_dt.replace(tzinfo=LOCAL_TZ).astimezone(timezone.utc).replace(tzinfo=None)


@bp.route('/')
@bp.route('/index')
@worker_required
def index():
    """维修工仪表盘首页"""
    user_filter = RepairOrder.assigned_workers.any(User.user_id == current_user.user_id)
    
    pending_count = db.session.scalar(
        select(func.count(RepairOrder.order_id)).where(
            user_filter,
            RepairOrder.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS])
        )
    )
    
    today_start, today_end = local_today_range()
    today_completed = db.session.scalar(
        select(func.count(RepairOrder.order_id)).where(
            user_filter,
            RepairOrder.status == OrderStatus.COMPLETED,
            RepairOrder.finish_time >= today_start,
            RepairOrder.finish_time < today_end
        )
    )
    
    week_start, week_end = local_week_range()
    week_completed = db.session.scalar(
        select(func.count(RepairOrder.order_id)).where(
            user_filter,
            RepairOrder.status == OrderStatus.COMPLETED,
            RepairOrder.finish_time >= week_start,
            RepairOrder.finish_time < week_end
        )
    )
    
    month_start, month_end = local_month_range()
    month_completed = db.session.scalar(
        select(func.count(RepairOrder.order_id)).where(
            user_filter,
            RepairOrder.status == OrderStatus.COMPLETED,
            RepairOrder.finish_time >= month_start,
            RepairOrder.finish_time < month_end
        )
    )
    
    urgent_tasks = db.session.execute(
        select(RepairOrder)
        .where(
            user_filter,
            RepairOrder.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS])
        )
        .order_by(RepairOrder.submit_time.asc())
        .limit(10)
        .options(
            joinedload(RepairOrder.building),
            selectinload(RepairOrder.assigned_workers)
        )
    ).scalars().all()
    
    return render_template(
        'worker/index.html',
        pending_count=pending_count,
        today_completed=today_completed,
        week_completed=week_completed,
        month_completed=month_completed,
        urgent_tasks=urgent_tasks
    )


@bp.route('/tasks')
@worker_required
def task_list():
    """我的待办"""
    user_filter = RepairOrder.assigned_workers.any(User.user_id == current_user.user_id)
    
    status_weight = case(
        (RepairOrder.status == OrderStatus.ASSIGNED, 1),
        (RepairOrder.status == OrderStatus.IN_PROGRESS, 2),
        else_=3
    )
    
    tasks = db.session.execute(
        select(RepairOrder)
        .where(
            user_filter,
            RepairOrder.status.in_([OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS])
        )
        .order_by(status_weight.asc(), RepairOrder.submit_time.desc())
        .options(
            joinedload(RepairOrder.building),
            selectinload(RepairOrder.assigned_workers),
            joinedload(RepairOrder.submitter)
        )
    ).scalars().all()
    
    my_finished_order_ids = db.session.execute(
        select(MaintenanceRecord.order_id).where(
            MaintenanceRecord.worker_id == current_user.user_id
        )
    ).scalars().all()
    
    return render_template(
        'worker/task_list.html',
        tasks=tasks,
        finished_ids=my_finished_order_ids,
        start_form=StartRepairForm(),
        posts_per_page=current_app.config.get('POSTS_PER_PAGE', 5)
    )


@bp.route('/start/<int:order_id>', methods=['POST'])
@worker_required
def start_task(order_id):
    """确认接单/开始维修"""
    form = StartRepairForm()
    if not form.validate_on_submit():
        return redirect(url_for('worker.task_list'))
    
    order = db.session.get(RepairOrder, order_id)
    if not order or current_user not in order.assigned_workers:
        flash('无权操作此工单', 'danger')
        return redirect(url_for('worker.task_list'))
    
    if order.status == OrderStatus.ASSIGNED:
        order.status = OrderStatus.IN_PROGRESS
        db.session.commit()
        flash('已确认开始维修，工单状态变更为"处理中"', 'success')
    else:
        flash('工单已处于处理中状态', 'info')
    
    return redirect(url_for('worker.task_list'))


@bp.route('/finish/<int:order_id>', methods=['GET', 'POST'])
@worker_required
def finish_order(order_id):
    """完工填报"""
    order = db.session.get(RepairOrder, order_id)
    
    if not order or current_user not in order.assigned_workers:
        flash('无权操作此工单', 'danger')
        return redirect(url_for('worker.task_list'))
    
    existing_record = db.session.execute(
        select(MaintenanceRecord).where(
            and_(
                MaintenanceRecord.order_id == order_id,
                MaintenanceRecord.worker_id == current_user.user_id
            )
        )
    ).scalar_one_or_none()
    
    if existing_record:
        flash('您已提交过该工单的维修记录，无需重复提交', 'warning')
        return redirect(url_for('worker.task_list'))
    
    form = MaintenanceReportForm()
    
    if request.method == 'GET':
        parts = db.session.execute(
            select(SparePart).where(SparePart.current_stock > 0)
        ).scalars().all()
        return render_template('worker/finish_form.html', order=order, form=form, parts=parts)
    
    if not form.validate_on_submit():
        parts = db.session.execute(
            select(SparePart).where(SparePart.current_stock > 0)
        ).scalars().all()
        return render_template('worker/finish_form.html', order=order, form=form, parts=parts)
    
    try:
        start_naive = form.start_time.data
        end_naive = form.end_time.data
        start_utc = naive_to_utc(start_naive)
        end_utc = naive_to_utc(end_naive)
        
        duration_hours = (end_naive - start_naive).total_seconds() / 3600
        labor_cost = round(duration_hours * HOURLY_RATE, 2)
        
        record = MaintenanceRecord(
            order_id=order.order_id,
            worker_id=current_user.user_id,
            start_time=start_utc,
            end_time=end_utc,
            result_desc=form.result_desc.data,
            labor_cost=labor_cost
        )
        db.session.add(record)
        db.session.flush()
        
        part_ids = request.form.getlist('part_ids[]')
        quantities = request.form.getlist('quantities[]')
        
        for pid_str, qty_str in zip(part_ids, quantities):
            qty = int(qty_str)
            if qty <= 0:
                continue
            
            part = db.session.get(SparePart, int(pid_str))
            if not part:
                raise ValueError(f"配件ID {pid_str} 不存在")
            
            if part.current_stock < qty:
                raise ValueError(f"配件【{part.part_name}】库存不足，剩余 {part.current_stock}")
            
            part.current_stock -= qty
            
            detail = PartUsageDetail(
                record_id=record.record_id,
                part_id=part.part_id,
                quantity=qty
            )
            db.session.add(detail)
        
        total_workers = len(order.assigned_workers)
        completed_count = db.session.scalar(
            select(func.count(MaintenanceRecord.record_id))
            .where(MaintenanceRecord.order_id == order.order_id)
        )
        
        if completed_count >= total_workers:
            order.status = OrderStatus.COMPLETED
            order.finish_time = datetime.now(timezone.utc)
            msg = '提交成功！所有维修人员均已完工，工单归档。'
        else:
            msg = f'提交成功！当前进度 ({completed_count}/{total_workers})，等待其他同事完工。'
        
        db.session.commit()
        flash(msg, 'success')
        return redirect(url_for('worker.task_list'))
    
    except ValueError as ve:
        db.session.rollback()
        flash(str(ve), 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Finish Order Error: {e}", exc_info=True)
        flash('系统处理失败，请重试', 'danger')
    
    parts = db.session.execute(
        select(SparePart).where(SparePart.current_stock > 0)
    ).scalars().all()
    return render_template('worker/finish_form.html', order=order, form=form, parts=parts)


@bp.route('/history')
@worker_required
def history():
    """维修历史"""
    history_orders = db.session.execute(
        select(RepairOrder)
        .where(
            RepairOrder.assigned_workers.any(User.user_id == current_user.user_id),
            RepairOrder.status == OrderStatus.COMPLETED
        )
        .order_by(RepairOrder.finish_time.desc())
        .options(
            joinedload(RepairOrder.building),
            selectinload(RepairOrder.assigned_workers),
            joinedload(RepairOrder.submitter)
        )
    ).scalars().all()
    
    return render_template(
        'worker/history.html',
        orders=history_orders,
        posts_per_page=current_app.config.get('POSTS_PER_PAGE', 5)
    )