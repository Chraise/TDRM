from flask import render_template, jsonify, request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import RepairOrder, SparePart, User, OrderStatus, DormBuilding, PartUsageDetail, MaintenanceRecord

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


@bp.route('/index', methods=['GET'])
@admin_required
def index():
    pending_count = db.session.scalar(
        select(func.count(RepairOrder.order_id))
        .where(RepairOrder.status == OrderStatus.PENDING)
    ) or 0

    low_stock_count = db.session.scalar(
        select(func.count(SparePart.part_id))
        .where(SparePart.current_stock < SparePart.warning_line)
    ) or 0

    # 使用上海时区计算月初，转换为UTC查询
    now_sh = datetime.now(SHANGHAI_TZ)
    month_start_sh = now_sh.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start_utc = month_start_sh.astimezone(timezone.utc)
    
    finished_monthly_count = db.session.scalar(
        select(func.count(RepairOrder.order_id))
        .where(
            RepairOrder.status == OrderStatus.COMPLETED,
            RepairOrder.finish_time >= month_start_utc
        )
    ) or 0

    total_users_count = db.session.scalar(
        select(func.count(User.user_id))
    ) or 0

    return render_template(
        'admin/index.html',
        pending_count=pending_count,
        low_stock_count=low_stock_count,
        finished_monthly_count=finished_monthly_count,
        total_users_count=total_users_count
    )


@bp.route('/api/dashboard/stats', methods=['GET'])
@admin_required
def dashboard_stats():
    """仪表板统计数据：趋势、状态分布、Top 5 楼宇、配件消耗"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        now_sh = datetime.now(SHANGHAI_TZ)
        now = now_sh.astimezone(timezone.utc)
        if end_date_str:
            try:
                end_date_naive = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date_sh = end_date_naive.replace(tzinfo=SHANGHAI_TZ, hour=23, minute=59, second=59)
                end_date = end_date_sh.astimezone(timezone.utc)
            except ValueError:
                end_date = now
        else:
            end_date = now
        
        if start_date_str:
            try:
                start_date_naive = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date_sh = start_date_naive.replace(tzinfo=SHANGHAI_TZ, hour=0, minute=0, second=0)
                start_date = start_date_sh.astimezone(timezone.utc)
            except ValueError:
                start_date = end_date - timedelta(days=6)
        else:
            start_date = end_date - timedelta(days=6)
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        # 生成日期范围列表，用于填充缺失日期
        date_list = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        while current_date <= end_date_only:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        new_orders_query = (
            select(
                func.date(RepairOrder.submit_time).label('date'),
                func.count(RepairOrder.order_id).label('count')
            )
            .where(
                RepairOrder.submit_time >= start_date,
                RepairOrder.submit_time <= end_date
            )
            .group_by(func.date(RepairOrder.submit_time))
        )
        new_orders_result = db.session.execute(new_orders_query).all()
        new_orders_dict = {row.date.strftime('%Y-%m-%d'): row.count for row in new_orders_result}
        
        completed_orders_query = (
            select(
                func.date(RepairOrder.finish_time).label('date'),
                func.count(RepairOrder.order_id).label('count')
            )
            .where(
                RepairOrder.finish_time >= start_date,
                RepairOrder.finish_time <= end_date,
                RepairOrder.finish_time.isnot(None)
            )
            .group_by(func.date(RepairOrder.finish_time))
        )
        completed_orders_result = db.session.execute(completed_orders_query).all()
        completed_orders_dict = {row.date.strftime('%Y-%m-%d'): row.count for row in completed_orders_result}
        
        new_orders_data = [new_orders_dict.get(date, 0) for date in date_list]
        completed_orders_data = [completed_orders_dict.get(date, 0) for date in date_list]
        
        trend_data = {
            'dates': date_list,
            'new_orders': new_orders_data,
            'completed_orders': completed_orders_data
        }
        
        status_query = (
            select(
                RepairOrder.status,
                func.count(RepairOrder.order_id).label('count')
            )
            .group_by(RepairOrder.status)
        )
        status_result = db.session.execute(status_query).all()
        
        status_names = {
            OrderStatus.PENDING: '待处理',
            OrderStatus.ASSIGNED: '已派单',
            OrderStatus.IN_PROGRESS: '处理中',
            OrderStatus.COMPLETED: '已完成',
            OrderStatus.CANCELLED: '已取消'
        }
        
        status_labels = []
        status_data = []
        for row in status_result:
            status_labels.append(status_names.get(row.status, str(row.status.value)))
            status_data.append(row.count)
        
        status_distribution = {
            'labels': status_labels,
            'data': status_data
        }
        
        building_query = (
            select(
                DormBuilding.building_name,
                func.count(RepairOrder.order_id).label('order_count')
            )
            .join(RepairOrder, DormBuilding.building_id == RepairOrder.repair_building_id)
            .group_by(DormBuilding.building_id, DormBuilding.building_name)
            .order_by(func.count(RepairOrder.order_id).desc())
            .limit(5)
        )
        building_result = db.session.execute(building_query).all()
        
        top_buildings = {
            'labels': [row.building_name for row in building_result],
            'data': [row.order_count for row in building_result]
        }
        
        # 计算最近6个月的起始月份（包含当前月）
        if now_sh.month >= 6:
            start_month = now_sh.month - 5
            start_year = now_sh.year
        else:
            start_month = now_sh.month + 7
            start_year = now_sh.year - 1
        
        month_list = []
        month_labels = []
        current_month = start_month
        current_year = start_year
        for i in range(6):
            month_key = f"{current_year}-{current_month:02d}"
            month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                          '7月', '8月', '9月', '10月', '11月', '12月']
            month_labels.append(f"{current_year}年{month_names[current_month-1]}")
            month_list.append(month_key)
            
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        month_start_sh = datetime(start_year, start_month, 1, tzinfo=SHANGHAI_TZ).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_start_utc = month_start_sh.astimezone(timezone.utc)
        
        # 找出Top 5配件（基于最近6个月总使用量）
        top_parts_query = (
            select(
                PartUsageDetail.part_id,
                SparePart.part_name,
                func.sum(PartUsageDetail.quantity).label('total_quantity')
            )
            .join(MaintenanceRecord, PartUsageDetail.record_id == MaintenanceRecord.record_id)
            .join(RepairOrder, MaintenanceRecord.order_id == RepairOrder.order_id)
            .join(SparePart, PartUsageDetail.part_id == SparePart.part_id)
            .where(
                RepairOrder.finish_time >= month_start_utc,
                RepairOrder.finish_time <= now,
                RepairOrder.finish_time.isnot(None)
            )
            .group_by(PartUsageDetail.part_id, SparePart.part_name)
            .order_by(func.sum(PartUsageDetail.quantity).desc())
            .limit(5)
        )
        top_parts_result = db.session.execute(top_parts_query).all()
        
        if not top_parts_result:
            parts_consumption = {
                'labels': month_labels,
                'datasets': []
            }
        else:
            top_part_ids = [row.part_id for row in top_parts_result]
            top_part_names = {row.part_id: row.part_name for row in top_parts_result}
            
            parts_monthly_query = (
                select(
                    func.date_format(RepairOrder.finish_time, '%Y-%m').label('month'),
                    PartUsageDetail.part_id,
                    func.sum(PartUsageDetail.quantity).label('quantity')
                )
                .join(MaintenanceRecord, PartUsageDetail.record_id == MaintenanceRecord.record_id)
                .join(RepairOrder, MaintenanceRecord.order_id == RepairOrder.order_id)
                .where(
                    RepairOrder.finish_time >= month_start_utc,
                    RepairOrder.finish_time <= now,
                    RepairOrder.finish_time.isnot(None),
                    PartUsageDetail.part_id.in_(top_part_ids)
                )
                .group_by(
                    func.date_format(RepairOrder.finish_time, '%Y-%m'),
                    PartUsageDetail.part_id
                )
            )
            parts_monthly_result = db.session.execute(parts_monthly_query).all()
            
            monthly_data = {}
            for row in parts_monthly_result:
                month_key = row.month
                if month_key not in monthly_data:
                    monthly_data[month_key] = {}
                monthly_data[month_key][row.part_id] = row.quantity
            
            part_colors = [
                '#4e73df',  # Primary Blue
                '#1cc88a',  # Success Green
                '#36b9cc',  # Info Cyan
                '#f6c23e',  # Warning Yellow
                '#e74a3b'   # Danger Red
            ]
            
            datasets = []
            for idx, part_id in enumerate(top_part_ids):
                part_name = top_part_names[part_id]
                data_array = []
                
                for month_key in month_list:
                    quantity = monthly_data.get(month_key, {}).get(part_id, 0)
                    data_array.append(quantity)
                
                datasets.append({
                    'label': part_name,
                    'data': data_array,
                    'backgroundColor': part_colors[idx % len(part_colors)]
                })
            
            parts_consumption = {
                'labels': month_labels,
                'datasets': datasets
            }
        
        return jsonify({
            'success': True,
            'data': {
                'trend': trend_data,
                'status_distribution': status_distribution,
                'top_buildings': top_buildings,
                'parts_consumption': parts_consumption
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500