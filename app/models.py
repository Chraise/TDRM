"""
数据库模型定义 (SQLAlchemy 2.0 Modern Style)
对应 init.sql 中的表结构
"""
from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from flask_login import UserMixin
from sqlalchemy import (
    String, Integer, SmallInteger, Text,
    ForeignKey, UniqueConstraint, CheckConstraint,
    Numeric
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, WriteOnlyMapped
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
import jwt
from app import db, login_manager


# ==================== 枚举类型定义 ====================
class UserRole(Enum):
    """用户角色枚举"""
    STUDENT = 'Student'
    WORKER = 'Worker'
    ADMIN = 'Admin'


class OrderStatus(Enum):
    """报修单状态枚举"""
    PENDING = 'Pending'          # 待处理
    ASSIGNED = 'Assigned'        # 已派单
    IN_PROGRESS = 'InProgress'   # 处理中
    COMPLETED = 'Completed'      # 已完成
    CANCELLED = 'Cancelled'      # 已取消

# ==================== 多对多关联表 ====================
order_assign = db.Table(
    'order_assign',
    db.Column('user_id', Integer, ForeignKey('sys_user.user_id'), primary_key=True),
    db.Column('order_id', Integer, ForeignKey('repair_order.order_id'), primary_key=True)
)

# ==================== 模型定义 ====================
class DormBuilding(db.Model):
    """宿舍楼模型"""
    __tablename__ = 'dorm_building'

    building_id: Mapped[int] = mapped_column(primary_key=True, comment='楼宇ID')
    building_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment='楼名')
    location: Mapped[Optional[str]] = mapped_column(String(100), comment='地理位置')
    admin_contact: Mapped[Optional[str]] = mapped_column(String(20), comment='宿管办公室电话')

    # 以下使用 WriteOnlyMapped 而不使用 Mapped，因为一栋楼对应的 user 和 repair_orders 可能比较多
    users: WriteOnlyMapped["User"] = relationship(back_populates="building")
    repair_orders: WriteOnlyMapped["RepairOrder"] = relationship(back_populates="building")

    def __repr__(self):
        return f'<DormBuilding {self.building_name}>'


class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'sys_user'

    user_id: Mapped[int] = mapped_column(primary_key=True, comment='用户ID')
    account: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment='登录账号')
    username: Mapped[str] = mapped_column(String(50), index=True, comment='姓名')
    password: Mapped[str] = mapped_column(String(256), comment='登录密码')
    role: Mapped[UserRole] = mapped_column(index=True, comment='角色')
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, comment='邮箱')
    building_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('dorm_building.building_id', ondelete='SET NULL', onupdate='CASCADE'),
        comment='所属宿舍楼ID'
    )
    room_no: Mapped[Optional[str]] = mapped_column(String(10), comment='房间号')
    status: Mapped[int] = mapped_column(SmallInteger, default=1, index=True, comment='状态: 1-在校/在职, 0-离校/离职')

    building: Mapped[Optional["DormBuilding"]] = relationship(back_populates="users")
    submitted_orders: WriteOnlyMapped["RepairOrder"] = relationship(
        back_populates="submitter",
        foreign_keys="[RepairOrder.submitter_id]"
    )
    assigned_orders: Mapped[List["RepairOrder"]] = relationship(
        secondary=order_assign,
        back_populates="assigned_workers"
    ) # 这里使用 list 因为一个工单不会被分配给很多的工人
    maintenance_records: WriteOnlyMapped["MaintenanceRecord"] = relationship(back_populates="worker")

    # Flask-Login 方法
    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_worker(self):
        return self.role == UserRole.WORKER

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    @property
    def is_active(self):
        return self.status == 1

    def get_reset_password_token(self, expires_in=600):
        """生成重置密码的 token"""
        return jwt.encode(
            {'reset_password': self.user_id, 'exp': int(datetime.now(timezone.utc).timestamp()) + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        """验证重置密码的 token 并返回 User 对象"""
        try:
            user_id = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )['reset_password']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        return db.session.get(User, user_id)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class SparePart(db.Model):
    """配件库存模型"""
    __tablename__ = 'spare_part'
    __table_args__ = (
        UniqueConstraint('part_name', 'spec', name='uq_part_name_spec'),
        CheckConstraint('current_stock >= 0', name='ck_stock_non_negative'),
    )

    part_id: Mapped[int] = mapped_column(primary_key=True, comment='配件ID')
    part_name: Mapped[str] = mapped_column(String(100), index=True, comment='配件名称')
    spec: Mapped[Optional[str]] = mapped_column(String(50), comment='规格型号')
    current_stock: Mapped[int] = mapped_column(default=0, comment='当前库存量')
    unit: Mapped[Optional[str]] = mapped_column(String(10), comment='单位')
    warning_line: Mapped[int] = mapped_column(default=10, comment='预警阈值')
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.00, comment='实时价格')

    usage_details: Mapped[List["PartUsageDetail"]] = relationship(back_populates="part")

    @property
    def is_low_stock(self):
        return self.current_stock < self.warning_line

    @property
    def full_name(self):
        if self.spec:
            return f"{self.part_name} ({self.spec})"
        return self.part_name

    def reduce_stock(self, quantity):
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("扣减数量必须为正整数")
        if self.current_stock < quantity:
            raise ValueError(f"库存不足！当前只有 {self.current_stock} {self.unit}")
        self.current_stock -= quantity
    # 这里扣减库存可能存在并发控制问题

    def __repr__(self):
        return f'<SparePart {self.part_name} (库存: {self.current_stock})>'


class RepairOrder(db.Model):
    """报修单模型"""
    __tablename__ = 'repair_order'

    order_id: Mapped[int] = mapped_column(primary_key=True, comment='报修单ID')
    submitter_id: Mapped[int] = mapped_column(
        ForeignKey('sys_user.user_id', ondelete='RESTRICT', onupdate='CASCADE'),
        comment='报修人ID'
    )
    repair_building_id: Mapped[int] = mapped_column(
        ForeignKey('dorm_building.building_id', ondelete='RESTRICT', onupdate='CASCADE'),
        comment='故障所在楼ID'
    )
    repair_location: Mapped[str] = mapped_column(String(10), comment='故障位置')
    title: Mapped[str] = mapped_column(String(100), comment='报修主题')
    description: Mapped[Optional[str]] = mapped_column(Text, comment='详细描述')
    image_urls: Mapped[Optional[str]] = mapped_column(Text, comment='故障图片url')
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.PENDING, comment='状态')
    submit_time: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), comment='提交时间')
    finish_time: Mapped[Optional[datetime]] = mapped_column(comment='实际完成时间')
    rating: Mapped[Optional[int]] = mapped_column(SmallInteger, comment='学生评分')
    feedback: Mapped[Optional[str]] = mapped_column(String(255), comment='学生反馈')

    submitter: Mapped["User"] = relationship(
        back_populates="submitted_orders",
        foreign_keys=[submitter_id]
    )
    building: Mapped["DormBuilding"] = relationship(back_populates="repair_orders")
    assigned_workers: Mapped[List["User"]] = relationship(
        secondary=order_assign,
        back_populates="assigned_orders"
    )
    maintenance_records: Mapped[Optional[List["MaintenanceRecord"]]] = relationship(back_populates="order")

    @property
    def is_pending(self):
        return self.status == OrderStatus.PENDING

    @property
    def is_assigned(self): return self.status == OrderStatus.ASSIGNED
    @property
    def is_in_progress(self): return self.status == OrderStatus.IN_PROGRESS
    @property
    def is_completed(self): return self.status == OrderStatus.COMPLETED
    @property
    def is_cancelled(self): return self.status == OrderStatus.CANCELLED

    def __repr__(self):
        return f'<RepairOrder {self.order_id}: {self.title} ({self.status})>'


class MaintenanceRecord(db.Model):
    """维修记录模型"""
    __tablename__ = 'maintenance_record'

    record_id: Mapped[int] = mapped_column(primary_key=True, comment='记录ID')
    order_id: Mapped[int] = mapped_column(ForeignKey('repair_order.order_id', ondelete='RESTRICT', onupdate='CASCADE'), comment='关联报修单ID')
    worker_id: Mapped[int] = mapped_column(ForeignKey('sys_user.user_id', ondelete='RESTRICT', onupdate='CASCADE'), comment='实际维修人ID')
    start_time: Mapped[Optional[datetime]] = mapped_column(comment='开始维修时间')
    end_time: Mapped[Optional[datetime]] = mapped_column(comment='结束维修时间')
    result_desc: Mapped[Optional[str]] = mapped_column(Text, comment='维修结果/故障原因分析')
    labor_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), comment='人工/时间成本估算')

    order: Mapped["RepairOrder"] = relationship(back_populates="maintenance_records")
    worker: Mapped["User"] = relationship(back_populates="maintenance_records")
    part_usage_details: Mapped[List["PartUsageDetail"]] = relationship(back_populates="maintenance_record")

    def __repr__(self):
        return f'<MaintenanceRecord {self.record_id} for Order {self.order_id}>'


class PartUsageDetail(db.Model):
    """配件消耗明细模型"""
    __tablename__ = 'part_usage_detail'

    usage_id: Mapped[int] = mapped_column(primary_key=True, comment='流水号')
    record_id: Mapped[int] = mapped_column(
        ForeignKey('maintenance_record.record_id', ondelete='RESTRICT', onupdate='CASCADE'),
        comment='关联维修记录ID'
    )
    part_id: Mapped[int] = mapped_column(
        ForeignKey('spare_part.part_id', ondelete='RESTRICT', onupdate='CASCADE'),
        comment='关联配件ID'
    )
    quantity: Mapped[int] = mapped_column(comment='消耗数量')

    maintenance_record: Mapped["MaintenanceRecord"] = relationship(back_populates="part_usage_details")
    part: Mapped["SparePart"] = relationship(back_populates="usage_details")
    
    def __repr__(self):
        return f'<PartUsageDetail {self.usage_id}: {self.quantity} x Part {self.part_id}>'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))