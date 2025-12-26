"""
初始化测试数据脚本
用于添加一些测试用户和宿舍楼数据
"""
from app import create_app, db
from app.models import User, DormBuilding, UserRole


def init_data():
    """初始化测试数据"""
    app = create_app()
    
    with app.app_context():
        # 检查是否已有数据
        if User.query.first():
            print("数据库中已存在用户数据，跳过初始化")
            return
        
        # 创建宿舍楼
        buildings = [
            DormBuilding(building_id=1, building_name='1号宿舍楼', location='东区', admin_contact='010-12345678'),
            DormBuilding(building_id=2, building_name='2号宿舍楼', location='东区', admin_contact='010-12345679'),
            DormBuilding(building_id=3, building_name='3号宿舍楼', location='西区', admin_contact='010-12345680'),
            DormBuilding(building_id=4, building_name='4号宿舍楼', location='西区', admin_contact='010-12345681'),
        ]
        
        for building in buildings:
            db.session.add(building)
        db.session.commit()
        print(f"已创建 {len(buildings)} 栋宿舍楼")
        
        # 创建管理员
        admin = User(
            user_id=1,
            account='10000001',
            username='系统管理员',
            role=UserRole.ADMIN,
            email='admin@example.com',
            status=1
        )
        admin.set_password('123456')
        db.session.add(admin)
        
        # 创建学生用户
        students = [
            {'user_id': 2, 'account': '20210001', 'username': '张三', 'email': 'zhangsan@example.com', 'building_id': 1, 'room_no': '101'},
            {'user_id': 3, 'account': '20210002', 'username': '李四', 'email': 'lisi@example.com', 'building_id': 1, 'room_no': '102'},
            {'user_id': 4, 'account': '20210003', 'username': '王五', 'email': 'wangwu@example.com', 'building_id': 2, 'room_no': '201'},
            {'user_id': 5, 'account': '20210004', 'username': '赵六', 'email': 'zhaoliu@example.com', 'building_id': 2, 'room_no': '202'},
            {'user_id': 6, 'account': '20210005', 'username': '钱七', 'email': 'qianqi@example.com', 'building_id': 3, 'room_no': '301'},
        ]
        
        for student_data in students:
            student = User(**student_data, role=UserRole.STUDENT, status=1)
            student.set_password('123456')
            db.session.add(student)
        
        # 创建工人用户
        workers = [
            {'user_id': 7, 'account': '50000001', 'username': '维修工甲', 'email': 'worker1@example.com', 'building_id': 1},
            {'user_id': 8, 'account': '50000002', 'username': '维修工乙', 'email': 'worker2@example.com', 'building_id': 2},
            {'user_id': 9, 'account': '50000003', 'username': '维修工丙', 'email': 'worker3@example.com', 'building_id': 3},
            {'user_id': 10, 'account': '50000004', 'username': '维修工丁', 'email': 'worker4@example.com', 'building_id': 4},
        ]
        
        for worker_data in workers:
            worker = User(**worker_data, role=UserRole.WORKER, status=1)
            worker.set_password('123456')
            db.session.add(worker)
        
        db.session.commit()
        print(f"已创建 1 个管理员")
        print(f"已创建 {len(students)} 个学生用户")
        print(f"已创建 {len(workers)} 个工人用户")
        print("\n测试账号信息：")
        print("管理员: 10000001 / 123456")
        print("学生: 20210001-20210005 / 123456")
        print("工人: 50000001-50000004 / 123456")


if __name__ == '__main__':
    init_data()

