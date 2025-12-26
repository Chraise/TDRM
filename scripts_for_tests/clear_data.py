"""
清空数据库数据脚本
清空所有表的数据，但保留表结构
"""
from app import create_app, db
from app.models import (
    PartUsageDetail, MaintenanceRecord, RepairOrder,
    User, SparePart, DormBuilding
)
from sqlalchemy import text


def clear_data():
    """清空所有表的数据，保留表结构"""
    app = create_app()
    
    with app.app_context():
        try:
            # 禁用外键检查（SQLite）
            if 'sqlite' in db.engine.url.drivername:
                db.session.execute(text('PRAGMA foreign_keys = OFF'))
            
            # 按照外键依赖关系的逆序删除数据
            # 1. 删除配件消耗明细（依赖维修记录）
            deleted = db.session.query(PartUsageDetail).delete()
            print(f"已清空 part_usage_detail 表: {deleted} 条记录")
            
            # 2. 删除维修记录（依赖报修单和用户）
            deleted = db.session.query(MaintenanceRecord).delete()
            print(f"已清空 maintenance_record 表: {deleted} 条记录")
            
            # 3. 删除多对多关联表 order_assign
            db.session.execute(text('DELETE FROM order_assign'))
            print("已清空 order_assign 表")
            
            # 4. 删除报修单（依赖用户和宿舍楼）
            deleted = db.session.query(RepairOrder).delete()
            print(f"已清空 repair_order 表: {deleted} 条记录")
            
            # 5. 删除用户（依赖宿舍楼）
            deleted = db.session.query(User).delete()
            print(f"已清空 sys_user 表: {deleted} 条记录")
            
            # 6. 删除配件库存（独立表）
            deleted = db.session.query(SparePart).delete()
            print(f"已清空 spare_part 表: {deleted} 条记录")
            
            # 7. 删除宿舍楼（可能被其他表依赖，最后删除）
            deleted = db.session.query(DormBuilding).delete()
            print(f"已清空 dorm_building 表: {deleted} 条记录")
            
            # 重新启用外键检查
            if 'sqlite' in db.engine.url.drivername:
                db.session.execute(text('PRAGMA foreign_keys = ON'))
            
            db.session.commit()
            print("\n✅ 所有表数据已清空，表结构已保留")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 清空数据时发生错误: {e}")
            raise


if __name__ == '__main__':
    clear_data()


