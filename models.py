"""
数据库模型定义
对应 init.sql 中的表结构
"""
from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ==================== 枚举类型定义 ====================
class UserRole:
    """用户角色枚举"""
    STUDENT = 'Student'
    WORKER = 'Worker'
    ADMIN = 'Admin'


class OrderStatus:
    """报修单状态枚举"""
    PENDING = 'Pending'          # 待处理
    ASSIGNED = 'Assigned'        # 已派单
    IN_PROGRESS = 'InProgress'   # 处理中
    COMPLETED = 'Completed'      # 已完成
    CANCELLED = 'Cancelled'      # 已取消


# ==================== 模型定义 ====================

class DormBuilding(db.Model):
    """宿舍楼模型"""
    __tablename__ = 'dorm_building'
    
    building_id = db.Column(db.Integer, primary_key=True, comment='楼宇ID')
    building_name = db.Column(db.String(50), nullable=False, comment='楼名')
    location = db.Column(db.String(100), nullable=True, comment='地理位置')
    admin_contact = db.Column(db.String(20), nullable=True, comment='宿管办公室电话')
    
    # 关联关系
    users = db.relationship('User', backref='building', lazy='dynamic', foreign_keys='User.building_id')
    repair_orders = db.relationship('RepairOrder', backref='building', lazy='dynamic')
    
    def __repr__(self):
        return f'<DormBuilding {self.building_name}>'


class User(UserMixin, db.Model):
    """用户模型（实现 Flask-Login 的 UserMixin）"""
    __tablename__ = 'sys_user'
    
    user_id = db.Column(db.Integer, primary_key=True, comment='用户ID')
    username = db.Column(db.String(50), nullable=False, comment='姓名')
    password = db.Column(db.String(100), nullable=False, comment='登录密码')
    role = db.Column(db.Enum('Student', 'Worker', 'Admin'), nullable=False, comment='角色')
    contact = db.Column(db.String(20), nullable=True, comment='联系电话')
    building_id = db.Column(db.Integer, db.ForeignKey('dorm_building.building_id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True, comment='所属宿舍楼ID')
    room_no = db.Column(db.String(10), nullable=True, comment='房间号')
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment='状态: 1-在校/在职, 0-离校/离职')
    
    # 关联关系
    submitted_orders = db.relationship('RepairOrder', backref='submitter', lazy='dynamic', foreign_keys='RepairOrder.submitter_id')
    assigned_orders = db.relationship('RepairOrder', backref='assigned_worker', lazy='dynamic', foreign_keys='RepairOrder.assigned_to')
    maintenance_records = db.relationship('MaintenanceRecord', backref='worker', lazy='dynamic')
    
    # Flask-Login 要求的方法
    def get_id(self):
        """返回用户ID（字符串形式）"""
        return str(self.user_id)
    
    def set_password(self, password):
        """设置密码（加密存储）"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password, password)
    
    @property
    def is_student(self):
        """判断是否为学生"""
        return self.role == UserRole.STUDENT
    
    @property
    def is_worker(self):
        """判断是否为维修人员"""
        return self.role == UserRole.WORKER
    
    @property
    def is_admin(self):
        """判断是否为管理员"""
        return self.role == UserRole.ADMIN
    
    @property
    def is_active_user(self):
        """判断用户是否在校/在职"""
        return self.status == 1
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class SparePart(db.Model):
    """配件库存模型"""
    __tablename__ = 'spare_part'
    
    part_id = db.Column(db.Integer, primary_key=True, comment='配件ID')
    part_name = db.Column(db.String(100), nullable=False, comment='配件名称')
    spec = db.Column(db.String(50), nullable=True, comment='规格型号')
    current_stock = db.Column(db.Integer, nullable=False, default=0, comment='当前库存量')
    unit = db.Column(db.String(10), nullable=True, comment='单位')
    warning_line = db.Column(db.Integer, nullable=False, default=10, comment='预警阈值')
    
    # 关联关系
    usage_details = db.relationship('PartUsageDetail', backref='part', lazy='dynamic')
    
    @property
    def is_low_stock(self):
        """判断是否库存不足（低于预警线）"""
        return self.current_stock < self.warning_line
    
    def __repr__(self):
        return f'<SparePart {self.part_name} (库存: {self.current_stock})>'


class RepairOrder(db.Model):
    """报修单模型"""
    __tablename__ = 'repair_order'
    
    order_id = db.Column(db.Integer, primary_key=True, comment='报修单ID')
    submitter_id = db.Column(db.Integer, db.ForeignKey('sys_user.user_id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, comment='报修人ID')
    building_id = db.Column(db.Integer, db.ForeignKey('dorm_building.building_id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, comment='故障所在楼ID')
    room_no = db.Column(db.String(10), nullable=False, comment='故障所在房间号')
    title = db.Column(db.String(100), nullable=False, comment='报修主题')
    description = db.Column(db.Text, nullable=True, comment='详细描述')
    status = db.Column(db.String(20), nullable=False, default=OrderStatus.PENDING, comment='状态')
    assigned_to = db.Column(db.Integer, db.ForeignKey('sys_user.user_id', ondelete='SET NULL', onupdate='CASCADE'), nullable=True, comment='被指派的维修员ID')
    submit_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment='提交时间')
    finish_time = db.Column(db.DateTime, nullable=True, comment='实际完成时间')
    
    # 关联关系
    maintenance_record = db.relationship('MaintenanceRecord', backref='order', uselist=False)  # 一对一关系
    
    @property
    def is_pending(self):
        """判断是否为待处理状态"""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_assigned(self):
        """判断是否已派单"""
        return self.status == OrderStatus.ASSIGNED
    
    @property
    def is_in_progress(self):
        """判断是否处理中"""
        return self.status == OrderStatus.IN_PROGRESS
    
    @property
    def is_completed(self):
        """判断是否已完成"""
        return self.status == OrderStatus.COMPLETED
    
    @property
    def is_cancelled(self):
        """判断是否已取消"""
        return self.status == OrderStatus.CANCELLED
    
    def __repr__(self):
        return f'<RepairOrder {self.order_id}: {self.title} ({self.status})>'


class MaintenanceRecord(db.Model):
    """维修记录模型"""
    __tablename__ = 'maintenance_record'
    
    record_id = db.Column(db.Integer, primary_key=True, comment='记录ID')
    order_id = db.Column(db.Integer, db.ForeignKey('repair_order.order_id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, unique=True, comment='关联报修单ID')
    worker_id = db.Column(db.Integer, db.ForeignKey('sys_user.user_id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, comment='实际维修人ID')
    start_time = db.Column(db.DateTime, nullable=True, comment='开始维修时间')
    end_time = db.Column(db.DateTime, nullable=True, comment='结束维修时间')
    result_desc = db.Column(db.Text, nullable=True, comment='维修结果/故障原因分析')
    labor_cost = db.Column(db.Numeric(10, 2), nullable=True, comment='人工/时间成本估算')
    
    # 关联关系
    part_usage_details = db.relationship('PartUsageDetail', backref='maintenance_record', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def repair_duration_minutes(self):
        """计算维修耗时（分钟）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def response_duration_hours(self):
        """计算响应耗时（小时）- 从报修提交到维修结束"""
        if self.order and self.order.submit_time and self.end_time:
            delta = self.end_time - self.order.submit_time
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    def __repr__(self):
        return f'<MaintenanceRecord {self.record_id} for Order {self.order_id}>'


class PartUsageDetail(db.Model):
    """配件消耗明细模型"""
    __tablename__ = 'part_usage_detail'
    
    usage_id = db.Column(db.Integer, primary_key=True, comment='流水号')
    record_id = db.Column(db.Integer, db.ForeignKey('maintenance_record.record_id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, comment='关联维修记录ID')
    part_id = db.Column(db.Integer, db.ForeignKey('spare_part.part_id', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False, comment='关联配件ID')
    quantity = db.Column(db.Integer, nullable=False, comment='消耗数量')
    
    def __repr__(self):
        return f'<PartUsageDetail {self.usage_id}: {self.quantity} x Part {self.part_id}>'

