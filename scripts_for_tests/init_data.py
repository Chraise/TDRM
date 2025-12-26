"""
初始化测试数据脚本
用于添加一些测试用户和宿舍楼数据
"""
from datetime import datetime, timezone, timedelta
from app import create_app, db
from app.models import User, DormBuilding, UserRole, RepairOrder, OrderStatus, MaintenanceRecord


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
        
        # 创建报修工单测试数据
        # 获取学生用户用于创建工单
        student1 = User.query.filter_by(account='20210001').first()  # 张三
        student2 = User.query.filter_by(account='20210002').first()  # 李四
        student3 = User.query.filter_by(account='20210003').first()  # 王五
        student4 = User.query.filter_by(account='20210004').first()  # 赵六
        student5 = User.query.filter_by(account='20210005').first()  # 钱七
        
        # 获取工人用户
        worker1 = User.query.filter_by(account='50000001').first()  # 维修工甲
        worker2 = User.query.filter_by(account='50000002').first()  # 维修工乙
        worker3 = User.query.filter_by(account='50000003').first()  # 维修工丙
        worker4 = User.query.filter_by(account='50000004').first()  # 维修工丁
        
        # 获取宿舍楼
        building1 = DormBuilding.query.filter_by(building_id=1).first()
        building2 = DormBuilding.query.filter_by(building_id=2).first()
        building3 = DormBuilding.query.filter_by(building_id=3).first()
        
        # 创建不同状态的工单
        now = datetime.now(timezone.utc)
        
        orders = [
            # Pending 状态 - 待处理
            RepairOrder(
                order_id=1,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='水龙头漏水',
                description='洗手间水龙头一直漏水，需要维修',
                status=OrderStatus.PENDING,
                submit_time=now - timedelta(days=2)
            ),
            # Assigned 状态 - 已派单
            RepairOrder(
                order_id=2,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='电灯不亮',
                description='房间内电灯突然不亮了，可能是线路问题',
                status=OrderStatus.ASSIGNED,
                submit_time=now - timedelta(days=5)
            ),
            # InProgress 状态 - 处理中
            RepairOrder(
                order_id=3,
                submitter_id=student2.user_id,
                repair_building_id=building1.building_id,
                repair_location='102',
                title='门锁损坏',
                description='房间门锁无法正常使用，需要更换',
                status=OrderStatus.IN_PROGRESS,
                submit_time=now - timedelta(days=3)
            ),
            # Completed 状态 - 已完成（未评价）
            RepairOrder(
                order_id=4,
                submitter_id=student2.user_id,
                repair_building_id=building1.building_id,
                repair_location='102',
                title='空调不制冷',
                description='空调制冷效果不好，需要检查',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=10),
                finish_time=now - timedelta(days=8),
                rating=None,
                feedback=None
            ),
            # Completed 状态 - 已完成（已评价）
            RepairOrder(
                order_id=5,
                submitter_id=student3.user_id,
                repair_building_id=building2.building_id,
                repair_location='201',
                title='网络接口故障',
                description='房间网络接口无法连接，无法上网',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=15),
                finish_time=now - timedelta(days=13),
                rating=5,
                feedback='维修及时，服务态度很好，问题已完全解决'
            ),
            # Completed 状态 - 已完成（未评价）
            RepairOrder(
                order_id=6,
                submitter_id=student3.user_id,
                repair_building_id=building2.building_id,
                repair_location='201',
                title='窗户关不严',
                description='窗户无法完全关闭，有缝隙漏风',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=7),
                finish_time=now - timedelta(days=5),
                rating=None,
                feedback=None
            ),
            # Cancelled 状态 - 已取消
            RepairOrder(
                order_id=7,
                submitter_id=student4.user_id,
                repair_building_id=building2.building_id,
                repair_location='202',
                title='热水器故障',
                description='热水器无法加热，报修后发现是误报，已自行解决',
                status=OrderStatus.CANCELLED,
                submit_time=now - timedelta(days=4)
            ),
            # Pending 状态 - 待处理
            RepairOrder(
                order_id=8,
                submitter_id=student4.user_id,
                repair_building_id=building2.building_id,
                repair_location='202',
                title='洗衣机故障',
                description='公共洗衣机无法正常使用，需要维修',
                status=OrderStatus.PENDING,
                submit_time=now - timedelta(days=1)
            ),
            # InProgress 状态 - 处理中
            RepairOrder(
                order_id=9,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='下水道堵塞',
                description='洗手间下水道堵塞，无法正常排水',
                status=OrderStatus.IN_PROGRESS,
                submit_time=now - timedelta(days=6)
            ),
            # Completed 状态 - 已完成（已评价，评分较低）
            RepairOrder(
                order_id=10,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='墙面裂缝',
                description='房间墙面出现裂缝，需要修补',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=20),
                finish_time=now - timedelta(days=18),
                rating=3,
                feedback='维修速度较慢，但最终问题得到解决'
            ),
            # 测试场景：带图片的工单 (Pending状态)
            RepairOrder(
                order_id=11,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='天花板漏水（有图片）',
                description='天花板有明显水渍，怀疑是楼上漏水导致',
                image_urls='uploads/test_image_1.jpg,uploads/test_image_2.jpg',
                status=OrderStatus.PENDING,
                submit_time=now - timedelta(hours=3)
            ),
            # 测试场景：没有详细描述的工单
            RepairOrder(
                order_id=12,
                submitter_id=student2.user_id,
                repair_building_id=building1.building_id,
                repair_location='102',
                title='门把手松动',
                description=None,  # 无描述
                status=OrderStatus.PENDING,
                submit_time=now - timedelta(hours=6)
            ),
            # 测试场景：多个指派工人的工单
            RepairOrder(
                order_id=13,
                submitter_id=student3.user_id,
                repair_building_id=building2.building_id,
                repair_location='201',
                title='电路故障（多人协作）',
                description='房间电路出现故障，可能需要多人协作维修',
                status=OrderStatus.ASSIGNED,
                submit_time=now - timedelta(days=4)
            ),
            # 测试场景：有多个维修记录的工单
            RepairOrder(
                order_id=14,
                submitter_id=student4.user_id,
                repair_building_id=building2.building_id,
                repair_location='202',
                title='暖气不热（多次维修）',
                description='暖气一直不热，之前维修过但问题仍然存在',
                status=OrderStatus.IN_PROGRESS,
                submit_time=now - timedelta(days=12)
            ),
            # 测试场景：Completed状态，1星评价
            RepairOrder(
                order_id=15,
                submitter_id=student5.user_id,
                repair_building_id=building3.building_id,
                repair_location='301',
                title='马桶堵塞',
                description='马桶严重堵塞，无法正常使用',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=25),
                finish_time=now - timedelta(days=23),
                rating=1,
                feedback='维修人员态度较差，问题反复出现'
            ),
            # 测试场景：Completed状态，2星评价
            RepairOrder(
                order_id=16,
                submitter_id=student5.user_id,
                repair_building_id=building3.building_id,
                repair_location='301',
                title='地漏反味',
                description='洗手间地漏有异味反出',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=30),
                finish_time=now - timedelta(days=28),
                rating=2,
                feedback='问题有所改善，但未完全解决'
            ),
            # 测试场景：Completed状态，4星评价
            RepairOrder(
                order_id=17,
                submitter_id=student1.user_id,
                repair_building_id=building1.building_id,
                repair_location='101',
                title='插座无电',
                description='房间内某个插座突然没电了',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=16),
                finish_time=now - timedelta(days=14),
                rating=4,
                feedback='维修及时，服务态度好，问题解决到位'
            ),
            # 测试场景：Assigned状态，但已开始维修（有维修记录）
            RepairOrder(
                order_id=18,
                submitter_id=student2.user_id,
                repair_building_id=building1.building_id,
                repair_location='102',
                title='门禁卡读卡器故障',
                description='房间门禁卡读卡器无法正常识别卡片',
                status=OrderStatus.ASSIGNED,
                submit_time=now - timedelta(days=7)
            ),
            # 测试场景：带图片且已完成（可评价）
            RepairOrder(
                order_id=19,
                submitter_id=student3.user_id,
                repair_building_id=building2.building_id,
                repair_location='201',
                title='地板翘起（有图片）',
                description='房间地板有部分区域翘起，有安全隐患',
                image_urls='uploads/test_image_3.jpg',
                status=OrderStatus.COMPLETED,
                submit_time=now - timedelta(days=9),
                finish_time=now - timedelta(days=7),
                rating=None,
                feedback=None
            ),
            # 测试场景：InProgress状态，有多个维修记录和多个指派工人
            RepairOrder(
                order_id=20,
                submitter_id=student4.user_id,
                repair_building_id=building2.building_id,
                repair_location='202',
                title='中央空调故障（复杂问题）',
                description='中央空调无法制冷，需要全面检修',
                status=OrderStatus.IN_PROGRESS,
                submit_time=now - timedelta(days=11)
            ),
        ]
        
        for order in orders:
            db.session.add(order)
        
        # 先提交工单，以便后续查询
        db.session.commit()
        
        # 为已派单和处理中的工单分配工人
        order2 = RepairOrder.query.filter_by(order_id=2).first()
        order3 = RepairOrder.query.filter_by(order_id=3).first()
        order9 = RepairOrder.query.filter_by(order_id=9).first()
        order13 = RepairOrder.query.filter_by(order_id=13).first()  # 多个工人
        order14 = RepairOrder.query.filter_by(order_id=14).first()  # 多次维修
        order18 = RepairOrder.query.filter_by(order_id=18).first()  # Assigned但已开始
        order20 = RepairOrder.query.filter_by(order_id=20).first()  # 复杂问题，多工人
        
        if order2 and worker1:
            order2.assigned_workers.append(worker1)
        if order3 and worker1:
            order3.assigned_workers.append(worker1)
        if order9 and worker2:
            order9.assigned_workers.append(worker2)
        # 场景：多个指派工人
        if order13 and worker1 and worker2:
            order13.assigned_workers.append(worker1)
            order13.assigned_workers.append(worker2)
        # 场景：多次维修的工单
        if order14 and worker3:
            order14.assigned_workers.append(worker3)
        # 场景：Assigned状态但已开始维修
        if order18 and worker2:
            order18.assigned_workers.append(worker2)
        # 场景：复杂问题，多个工人协作
        if order20 and worker1 and worker3:
            order20.assigned_workers.append(worker1)
            order20.assigned_workers.append(worker3)
        
        # 提交工人分配
        db.session.commit()
        
        # 为已完成的工单创建维修记录
        order4 = RepairOrder.query.filter_by(order_id=4).first()
        order5 = RepairOrder.query.filter_by(order_id=5).first()
        order6 = RepairOrder.query.filter_by(order_id=6).first()
        order10 = RepairOrder.query.filter_by(order_id=10).first()
        order14 = RepairOrder.query.filter_by(order_id=14).first()  # 多次维修
        order15 = RepairOrder.query.filter_by(order_id=15).first()  # 1星评价
        order16 = RepairOrder.query.filter_by(order_id=16).first()  # 2星评价
        order17 = RepairOrder.query.filter_by(order_id=17).first()  # 4星评价
        order18 = RepairOrder.query.filter_by(order_id=18).first()  # Assigned但已开始
        order19 = RepairOrder.query.filter_by(order_id=19).first()  # 已完成可评价
        order20 = RepairOrder.query.filter_by(order_id=20).first()  # 复杂问题，多记录
        
        maintenance_records = []
        record_id_counter = 1
        
        if order4 and worker1:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order4.order_id,
                    worker_id=worker1.user_id,
                    start_time=now - timedelta(days=9),
                    end_time=now - timedelta(days=8),
                    result_desc='检查发现空调滤网堵塞，已清洗滤网，制冷效果恢复正常',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        if order5 and worker1:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order5.order_id,
                    worker_id=worker1.user_id,
                    start_time=now - timedelta(days=14),
                    end_time=now - timedelta(days=13),
                    result_desc='网络接口模块损坏，已更换新的接口模块，网络连接正常',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        if order6 and worker2:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order6.order_id,
                    worker_id=worker2.user_id,
                    start_time=now - timedelta(days=6),
                    end_time=now - timedelta(days=5),
                    result_desc='窗户轨道变形，已调整轨道并更换密封条，窗户可正常关闭',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        if order10 and worker1:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order10.order_id,
                    worker_id=worker1.user_id,
                    start_time=now - timedelta(days=19),
                    end_time=now - timedelta(days=18),
                    result_desc='墙面裂缝已用腻子填补并重新粉刷，外观恢复正常',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：多次维修记录（第一次维修未解决）
        if order14 and worker3:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order14.order_id,
                    worker_id=worker3.user_id,
                    start_time=now - timedelta(days=11),
                    end_time=now - timedelta(days=10),
                    result_desc='第一次维修：清洗了暖气管道，但问题仍然存在，需要进一步检查',
                    labor_cost=None
                )
            )
            record_id_counter += 1
            # 第二次维修
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order14.order_id,
                    worker_id=worker3.user_id,
                    start_time=now - timedelta(days=10),
                    end_time=None,  # 测试：只有start_time，没有end_time
                    result_desc='第二次维修：发现是暖气阀门故障，正在更换中...',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：1星评价的维修记录
        if order15 and worker4:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order15.order_id,
                    worker_id=worker4.user_id,
                    start_time=now - timedelta(days=24),
                    end_time=now - timedelta(days=23),
                    result_desc='使用疏通工具处理，问题暂时解决，但可能存在反复',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：2星评价的维修记录
        if order16 and worker4:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order16.order_id,
                    worker_id=worker4.user_id,
                    start_time=now - timedelta(days=29),
                    end_time=now - timedelta(days=28),
                    result_desc='更换了地漏盖，异味有所减少，但未完全解决',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：4星评价的维修记录
        if order17 and worker1:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order17.order_id,
                    worker_id=worker1.user_id,
                    start_time=now - timedelta(days=15),
                    end_time=now - timedelta(days=14),
                    result_desc='检查发现是线路接触不良，已重新接线并加固，插座恢复正常使用',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：Assigned状态但已开始维修
        if order18 and worker2:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order18.order_id,
                    worker_id=worker2.user_id,
                    start_time=now - timedelta(days=6),
                    end_time=None,  # 只有start_time，维修中
                    result_desc='已检查读卡器，发现是连接线路问题，正在修复中',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：已完成可评价的维修记录
        if order19 and worker2:
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order19.order_id,
                    worker_id=worker2.user_id,
                    start_time=now - timedelta(days=8),
                    end_time=now - timedelta(days=7),
                    result_desc='地板翘起是由于受潮导致，已更换损坏的地板块，并做了防潮处理',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        # 场景：复杂问题，多个维修记录，多个工人
        if order20 and worker1 and worker3:
            # 第一个工人：初步检查
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order20.order_id,
                    worker_id=worker1.user_id,
                    start_time=now - timedelta(days=10),
                    end_time=now - timedelta(days=10),
                    result_desc='初步检查：发现是制冷剂泄漏，需要添加制冷剂',
                    labor_cost=None
                )
            )
            record_id_counter += 1
            # 第二个工人：添加制冷剂
            maintenance_records.append(
                MaintenanceRecord(
                    record_id=record_id_counter,
                    order_id=order20.order_id,
                    worker_id=worker3.user_id,
                    start_time=now - timedelta(days=10),
                    end_time=None,  # 只有start_time，正在处理
                    result_desc='正在添加制冷剂并检查是否还有其他故障',
                    labor_cost=None
                )
            )
            record_id_counter += 1
        
        for record in maintenance_records:
            db.session.add(record)
        
        db.session.commit()
        print(f"已创建 {len(orders)} 个报修工单")
        print(f"已创建 {len(maintenance_records)} 个维修记录")
        
        print("\n测试账号信息：")
        print("管理员: 10000001 / 123456")
        print("学生: 20210001-20210005 / 123456")
        print("工人: 50000001-50000004 / 123456")
        print("\n工单状态分布：")
        print(f"  - Pending (待处理): {len([o for o in orders if o.status == OrderStatus.PENDING])} 个")
        print(f"  - Assigned (已派单): {len([o for o in orders if o.status == OrderStatus.ASSIGNED])} 个")
        print(f"  - InProgress (处理中): {len([o for o in orders if o.status == OrderStatus.IN_PROGRESS])} 个")
        print(f"  - Completed (已完成): {len([o for o in orders if o.status == OrderStatus.COMPLETED])} 个")
        print(f"  - Cancelled (已取消): {len([o for o in orders if o.status == OrderStatus.CANCELLED])} 个")
        print("\n测试场景覆盖：")
        print("  ✓ 各种状态的工单（Pending, Assigned, InProgress, Completed, Cancelled）")
        print("  ✓ 带图片的工单（order_id: 11, 19）")
        print("  ✓ 无详细描述的工单（order_id: 12）")
        print("  ✓ 多个指派工人的工单（order_id: 13, 20）")
        print("  ✓ 多个维修记录的工单（order_id: 14, 20）")
        print("  ✓ 各种评分的工单（1-5星：order_id: 15, 16, 10, 17, 5）")
        print("  ✓ 可评价但未评价的工单（order_id: 4, 6, 19）")
        print("  ✓ 有start_time但没有end_time的维修记录")
        print("  ✓ Assigned状态但已开始维修的工单（order_id: 18）")
        print("\n推荐测试工单ID：")
        print("  - 测试Pending状态: 1, 8, 11, 12")
        print("  - 测试可评价功能: 4, 6, 19 (Completed且rating=None)")
        print("  - 测试已评价显示: 5 (5星), 10 (3星), 15 (1星), 16 (2星), 17 (4星)")
        print("  - 测试图片展示: 11, 19")
        print("  - 测试多个维修记录: 14, 20")
        print("  - 测试多个指派工人: 13, 20")
        print("  - 测试取消工单功能: 1, 8, 11, 12 (Pending状态)")


if __name__ == '__main__':
    init_data()

