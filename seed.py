import random
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from faker import Faker
from sqlalchemy import text

# ==================== 关键修改区域 ====================
from app import create_app, db
from app.models import (
    User, DormBuilding, RepairOrder, MaintenanceRecord,
    SparePart, PartUsageDetail, UserRole, OrderStatus
)

app = create_app()
# ====================================================

fake = Faker('zh_CN')

# ================= 配置参数 =================
BASE_DATE = datetime(2025, 12, 28, 12, 0, 0, tzinfo=timezone.utc)
TOTAL_STUDENTS = 80
TOTAL_WORKERS = 5
TOTAL_ORDERS = 150

# 清华风格的楼宇列表
TSINGHUA_BUILDINGS = [
    {"name": "紫荆学生公寓1号楼", "loc": "紫荆区东北侧"},
    {"name": "紫荆学生公寓2号楼", "loc": "紫荆区东侧"},
    {"name": "紫荆学生公寓3号楼", "loc": "紫荆区东南侧"},
    {"name": "南区宿舍30号楼", "loc": "学堂路西侧"},
    {"name": "南区宿舍31号楼", "loc": "学堂路西侧"},
    {"name": "文苑3号楼", "loc": "西北校区"},
]

# 常见维修配件
SPARE_PARTS_DATA = [
    {"name": "LED吸顶灯模组", "spec": "24W/白光", "unit": "个", "price": "18.5", "stock": 50},
    {"name": "公牛五孔插座", "spec": "86型/白色", "unit": "个", "price": "12.0", "stock": 100},
    {"name": "水龙头阀芯", "spec": "陶瓷片/通用", "unit": "个", "price": "5.0", "stock": 200},
    {"name": "空调遥控器", "spec": "格力/通用型", "unit": "个", "price": "25.0", "stock": 30},
    {"name": "门锁锁芯", "spec": "C级叶片锁", "unit": "套", "price": "45.0", "stock": 20},
    {"name": "马桶进水阀", "spec": "通用型", "unit": "个", "price": "15.0", "stock": 40},
    {"name": "网线水晶头", "spec": "RJ45/超五类", "unit": "个", "price": "0.5", "stock": 500},
]

REPAIR_ISSUES = [
    ("灯不亮了", "打开开关闪了一下就黑了，可能是灯管坏了"),
    ("厕所堵塞", "下水非常慢，并且有异味，请求疏通"),
    ("空调不制热", "开了30度还是吹冷风，遥控器有电"),
    ("阳台门锁坏了", "钥匙插不进去，现在门锁不上"),
    ("洗手池漏水", "水龙头关紧了还是滴水，一晚上接一盆"),
    ("网络接口没反应", "插网线电脑显示未连接，换了网线也不行"),
    ("椅子腿断了", "坐着坐着突然塌了，需要更换椅子"),
    ("天花板漏水", "楼上好像漏水，墙皮都泡鼓了"),
]

def generate_weighted_time():
    if random.random() < 0.8:
        days_offset = random.randint(0, 6)
    else:
        days_offset = random.randint(7, 90)
    seconds_offset = random.randint(0, 86400)
    event_time = BASE_DATE - timedelta(days=days_offset, seconds=seconds_offset)
    return event_time

def clean_database():
    print("🗑️  正在清理旧数据...")
    try:
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        tables = [
            'part_usage_detail', 'maintenance_record', 'order_assign',
            'repair_order', 'spare_part', 'sys_user', 'dorm_building'
        ]
        for table in tables:
            db.session.execute(text(f"TRUNCATE TABLE {table}"))
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
    except Exception as e:
        print(f"⚠️ 清理部分失败: {e}")
        db.session.rollback()

def seed_data():
    clean_database()
    print("🌱 开始生成数据...")

    # 1. 创建楼宇
    buildings = []
    for b_data in TSINGHUA_BUILDINGS:
        b = DormBuilding(
            building_name=b_data["name"],
            location=b_data["loc"],
            admin_contact=f"010-6278{random.randint(1000, 9999)}"
        )
        buildings.append(b)
    db.session.add_all(buildings)
    db.session.commit()
    print(f"✅ 已创建 {len(buildings)} 栋宿舍楼")

    # 2. 创建配件库存
    parts = []
    for p_data in SPARE_PARTS_DATA:
        p = SparePart(
            part_name=p_data["name"],
            spec=p_data["spec"],
            unit=p_data["unit"],
            price=Decimal(p_data["price"]),
            current_stock=p_data["stock"],
            warning_line=10
        )
        parts.append(p)
    db.session.add_all(parts)
    db.session.commit()
    print(f"✅ 已创建 {len(parts)} 种配件信息")

    # 3. 创建用户
    users = []
    
    # 3.1 管理员 (保持 admin, 如需 10 位数请改为 '2010000000')
    admin = User(
        account='admin',
        username='系统管理员',
        email='admin@tsinghua.edu.cn',
        role=UserRole.ADMIN,
        status=1
    )
    admin.set_password('admin123')
    users.append(admin)

    # 3.2 维修工 (10位数: 2020 + 99 + 0001~0005)
    workers = []
    worker_names = ['张师傅', '王师傅', '李师傅', '赵工', '刘工']
    for i in range(TOTAL_WORKERS):
        # 格式: 年份(4) + 部门码(2) + 序列号(4)
        worker_id = f"202099{i+1:04d}" 
        
        w = User(
            account=worker_id, 
            username=worker_names[i] if i < len(worker_names) else fake.name(),
            email=f'worker{i+1}@tsinghua.edu.cn',
            role=UserRole.WORKER,
            status=1
        )
        w.set_password('123456')
        workers.append(w)
        users.append(w)

    # 3.3 学生 (10位数: 年份 + 01 + 4位随机)
    students = []
    generated_accounts = set() # 防止随机数碰撞

    for i in range(TOTAL_STUDENTS):
        enroll_year = random.choice([2022, 2023, 2024, 2025])
        dept_code = "01" # 假设院系代码为 01
        
        # 循环生成直到不重复
        while True:
            rand_suffix = random.randint(1000, 9999) # 4位随机数
            student_id = f"{enroll_year}{dept_code}{rand_suffix}"
            if student_id not in generated_accounts:
                generated_accounts.add(student_id)
                break
        
        building = random.choice(buildings)
        room_no = f"{random.randint(1, 12)}0{random.randint(1, 9)}"

        s = User(
            account=student_id,
            username=fake.name(),
            email=f"{student_id}@mails.tsinghua.edu.cn",
            role=UserRole.STUDENT,
            building=building,
            room_no=room_no,
            status=1
        )
        s.set_password('123456')
        students.append(s)
        users.append(s)

    db.session.add_all(users)
    db.session.commit()
    print(f"✅ 已创建 {len(users)} 个用户")
    print(f"   - 管理员账号: admin")
    print(f"   - 维修工账号示例: 2020990001 (密码 123456)")
    print(f"   - 学生账号示例: {students[0].account} (密码 123456)")

    # 4. 创建报修单
    orders_created = 0
    for _ in range(TOTAL_ORDERS):
        student = random.choice(students)
        issue_title, issue_desc = random.choice(REPAIR_ISSUES)
        submit_time = generate_weighted_time()

        order = RepairOrder(
            submitter=student,
            repair_building_id=student.building_id,
            repair_location=student.room_no,
            title=issue_title,
            description=issue_desc,
            submit_time=submit_time,
            status=OrderStatus.PENDING
        )

        time_diff = BASE_DATE - submit_time
        hours_diff = time_diff.total_seconds() / 3600

        target_status = OrderStatus.PENDING
        if hours_diff > 48:
            target_status = random.choice([OrderStatus.COMPLETED] * 8 + [OrderStatus.CANCELLED])
        elif hours_diff > 12:
            target_status = random.choice([OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED])
        elif hours_diff > 2:
            target_status = random.choice([OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS])
        
        worker = None
        if target_status != OrderStatus.PENDING:
            worker = random.choice(workers)
            order.assigned_workers.append(worker)
            order.status = OrderStatus.ASSIGNED
        
        if target_status in [OrderStatus.IN_PROGRESS, OrderStatus.COMPLETED]:
            order.status = OrderStatus.IN_PROGRESS
        
        if target_status == OrderStatus.COMPLETED:
            fix_duration = timedelta(hours=random.randint(1, 48))
            finish_time = submit_time + fix_duration
            if finish_time > BASE_DATE:
                finish_time = BASE_DATE - timedelta(minutes=random.randint(10, 60))

            order.status = OrderStatus.COMPLETED
            order.finish_time = finish_time
            order.rating = random.choices([5, 4, 3, 1], weights=[70, 20, 5, 5])[0]
            order.feedback = random.choice(["师傅很专业", "修得很快", "态度很好", "一般般", "响应太慢了"]) if order.rating else None

            record = MaintenanceRecord(
                worker=worker,
                order=order,
                start_time=finish_time - timedelta(hours=1),
                end_time=finish_time,
                result_desc=f"已更换损坏的{issue_title[:2]}，测试正常。",
                labor_cost=Decimal(random.randint(50, 200))
            )
            
            if random.random() > 0.5:
                part = random.choice(parts)
                qty = random.randint(1, 2)
                usage = PartUsageDetail(
                    maintenance_record=record,
                    part=part,
                    quantity=qty
                )
                part.current_stock -= qty
                db.session.add(usage)
            
            db.session.add(record)

        elif target_status == OrderStatus.CANCELLED:
            order.status = OrderStatus.CANCELLED
            order.feedback = "学生自行解决了"

        db.session.add(order)
        orders_created += 1

    db.session.commit()
    print(f"✅ 已生成 {orders_created} 条报修单")
    print("🎉 数据库填充完成！")

if __name__ == '__main__':
    with app.app_context():
        try:
            seed_data()
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            traceback.print_exc()
            db.session.rollback()