from flask import render_template, jsonify, request
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from app import db
from app.admin import bp
from app.decorators import admin_required
from app.models import RepairOrder, SparePart, User, OrderStatus, DormBuilding, PartUsageDetail, MaintenanceRecord


@bp.route('/index', methods=['GET'])
@admin_required
def index():
    # 计算待处理工单数量
    pending_count = db.session.scalar(
        select(func.count(RepairOrder.order_id))
        .where(RepairOrder.status == OrderStatus.PENDING)
    ) or 0

    # 计算库存预警数量（current_stock < warning_line）
    low_stock_count = db.session.scalar(
        select(func.count(SparePart.part_id))
        .where(SparePart.current_stock < SparePart.warning_line)
    ) or 0

    # 计算本月已完工数量
    # 获取当前月份的第一天（UTC时间）
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    finished_monthly_count = db.session.scalar(
        select(func.count(RepairOrder.order_id))
        .where(
            RepairOrder.status == OrderStatus.COMPLETED,
            RepairOrder.finish_time >= month_start
        )
    ) or 0

    # 计算总用户数
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
    """
    仪表板统计数据 API 端点
    返回趋势数据、状态分布和 Top 5 楼宇数据
    """
    try:
        # 获取日期参数（可选）
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # 默认使用最近7天
        now = datetime.now(timezone.utc)
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                # 设置为当天的结束时间（23:59:59）
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                end_date = now
        else:
            end_date = now
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                # 设置为当天的开始时间（00:00:00）
                start_date = start_date.replace(hour=0, minute=0, second=0)
            except ValueError:
                start_date = end_date - timedelta(days=6)
        else:
            start_date = end_date - timedelta(days=6)
        
        # 确保 start_date <= end_date
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        # ========== 1. 趋势数据（按日期分组） ==========
        # 生成日期范围列表（用于填充缺失的日期）
        date_list = []
        current_date = start_date.date()
        end_date_only = end_date.date()
        while current_date <= end_date_only:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # 查询新订单数量（按 submit_time 分组）
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
        
        # 查询已完成订单数量（按 finish_time 分组）
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
        
        # 填充缺失的日期为 0
        new_orders_data = [new_orders_dict.get(date, 0) for date in date_list]
        completed_orders_data = [completed_orders_dict.get(date, 0) for date in date_list]
        
        trend_data = {
            'dates': date_list,
            'new_orders': new_orders_data,
            'completed_orders': completed_orders_data
        }
        
        # ========== 2. 状态分布 ==========
        status_query = (
            select(
                RepairOrder.status,
                func.count(RepairOrder.order_id).label('count')
            )
            .group_by(RepairOrder.status)
        )
        status_result = db.session.execute(status_query).all()
        
        # 状态名称映射（中文）
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
        
        # ========== 3. Top 5 楼宇（按订单数量） ==========
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
        
        # ========== 4. 配件消耗趋势（最近6个月，Top 5配件） ==========
        # 计算6个月前的起始月份（包含当前月，共6个月）
        if now.month >= 6:
            start_month = now.month - 5  # 包含当前月，所以是-5
            start_year = now.year
        else:
            start_month = now.month + 7  # 跨年
            start_year = now.year - 1
        
        # 生成最近6个月的月份列表（用于填充缺失月份）
        month_list = []
        month_labels = []
        current_month = start_month
        current_year = start_year
        for i in range(6):
            month_key = f"{current_year}-{current_month:02d}"
            # 月份标签（中文）
            month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                          '7月', '8月', '9月', '10月', '11月', '12月']
            month_labels.append(f"{current_year}年{month_names[current_month-1]}")
            month_list.append(month_key)
            
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        # 第一步：找出Top 5配件（基于最近6个月的总使用量）
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
                RepairOrder.finish_time >= datetime(start_year, start_month, 1, tzinfo=timezone.utc),
                RepairOrder.finish_time <= now,
                RepairOrder.finish_time.isnot(None)
            )
            .group_by(PartUsageDetail.part_id, SparePart.part_name)
            .order_by(func.sum(PartUsageDetail.quantity).desc())
            .limit(5)
        )
        top_parts_result = db.session.execute(top_parts_query).all()
        
        if not top_parts_result:
            # 如果没有数据，返回空结构
            parts_consumption = {
                'labels': month_labels,
                'datasets': []
            }
        else:
            top_part_ids = [row.part_id for row in top_parts_result]
            top_part_names = {row.part_id: row.part_name for row in top_parts_result}
            
            # 第二步：按月份和配件分组，求和数量
            # 使用SQLAlchemy的date_trunc或Python端处理月份
            parts_monthly_query = (
                select(
                    func.date_format(RepairOrder.finish_time, '%Y-%m').label('month'),
                    PartUsageDetail.part_id,
                    func.sum(PartUsageDetail.quantity).label('quantity')
                )
                .join(MaintenanceRecord, PartUsageDetail.record_id == MaintenanceRecord.record_id)
                .join(RepairOrder, MaintenanceRecord.order_id == RepairOrder.order_id)
                .where(
                    RepairOrder.finish_time >= datetime(start_year, start_month, 1, tzinfo=timezone.utc),
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
            
            # 第三步：数据转换 - 构建字典 {month: {part_id: quantity}}
            monthly_data = {}
            for row in parts_monthly_result:
                month_key = row.month
                if month_key not in monthly_data:
                    monthly_data[month_key] = {}
                monthly_data[month_key][row.part_id] = row.quantity
            
            # 第四步：为每个Top 5配件创建数据集
            # 颜色列表（SB Admin 2 标准颜色）
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
                
                # 为每个月份填充数据（如果没有则填0）
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
        
        # 返回 JSON 响应
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