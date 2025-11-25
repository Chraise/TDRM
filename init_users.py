"""
初始化测试用户
用于开发和测试
"""
from app import create_app
from extensions import db
from models import User, DormBuilding, UserRole

app = create_app()

with app.app_context():
    # 创建测试宿舍楼
    building = DormBuilding.query.filter_by(building_name='C楼').first()
    if not building:
        building = DormBuilding(
            building_name='C楼',
            location='清华大学',
            admin_contact='010-12345678'
        )
        db.session.add(building)
        db.session.commit()
        print("✓ 创建测试宿舍楼: C楼")
    
    # 创建测试用户
    users_data = [
        {
            'username': 'admin',
            'password': 'admin123',
            'role': UserRole.ADMIN,
            'contact': '13800138000',
            'building_id': building.building_id,
            'room_no': None,
            'status': 1
        },
        {
            'username': 'student1',
            'password': 'student123',
            'role': UserRole.STUDENT,
            'contact': '13800138001',
            'building_id': building.building_id,
            'room_no': '302',
            'status': 1
        },
        {
            'username': 'worker1',
            'password': 'worker123',
            'role': UserRole.WORKER,
            'contact': '13800138002',
            'building_id': building.building_id,
            'room_no': None,
            'status': 1
        }
    ]
    
    for user_data in users_data:
        username = user_data['username']
        user = User.query.filter_by(username=username).first()
        
        if not user:
            user = User(**user_data)
            user.set_password(user_data['password'])
            db.session.add(user)
            print(f"✓ 创建用户: {username} ({user_data['role']})")
        else:
            # 更新密码（如果用户已存在）
            user.set_password(user_data['password'])
            print(f"✓ 更新用户密码: {username}")
    
    db.session.commit()
    print("\n" + "="*50)
    print("用户初始化完成！")
    print("="*50)
    print("\n测试账号：")
    print("  管理员: admin / admin123")
    print("  学生:   student1 / student123")
    print("  维修人员: worker1 / worker123")
    print("\n可以访问 http://localhost:5000/auth/login 进行登录测试")

