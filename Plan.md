既然你已经完成了**数据库设计**、**Models编写**以及**登录/认证基础**，接下来的开发计划应该围绕设计文档中的**核心业务流（报修-派单-维修-耗材-评价）**展开。

由于你使用的是 Flask + 本地模板（Jinja2）不分离模式，建议按照**角色功能模块**进行划分。以下是详细的后续开发计划及关键代码思路：

---

### 第一阶段：基础设施与公共组件 (Infrastructure)
在开始写业务逻辑前，先完善通用的页面结构和权限控制。

1.  **基础布局模板 (`base.html`)**
    *   集成 Bootstrap（建议 v4 或 v5）以快速构建 UI。
    *   **导航栏逻辑**：根据 `current_user.role` 动态显示菜单。
        *   学生：我的报修、发起报修。
        *   维修工：待办工单、历史维修。
        *   管理员：工单调度、库存管理、数据报表。
2.  **权限装饰器 (`decorators.py`)**
    *   虽然你有 `login_required`，但需要区分角色。
    *   编写 `@admin_required`, `@worker_required`, `@student_required`，防止越权访问。

---

### 第二阶段：学生端 - 报修发起与闭环 (Student Module)
这是业务流程的起点和终点。

**功能点：**
1.  **发起报修 (Create Ticket)**
    *   **Route:** `/student/create_repair`
    *   **Logic:**
        *   从 `sys_user` 获取当前用户 ID 填入 `submitter_id`。
        *   从数据库加载 `dorm_building` 列表供选择（虽然用户有归属楼宇，但为了灵活可以默认选中所属楼宇）。
        *   状态默认为 `Pending`。
    *   **Form:** 标题、详情、上传图片（可选）、楼宇、房间号。
2.  **我的工单 (My Orders)**
    *   **Route:** `/student/my_orders`
    *   **Query:** `RepairOrder.query.filter_by(submitter_id=current_user.id)`。
    *   **UI:** 列表展示，不同状态（Pending/Processing/Done）显示不同颜色标签。
3.  **评价工单 (Rate)**
    *   **Logic:** 只有状态为 `Finished` 且 `rating` 为空的工单可以评价。
    *   **Action:** 更新 `repair_order` 表的 `rating` 字段。

---

### 第三阶段：管理员端 - 调度与管理 (Admin Module)
这是业务流程的枢纽。

**功能点：**
1.  **工单池与派单 (Dispatch)**
    *   **Route:** `/admin/orders`
    *   **UI:** 表格展示所有工单。
    *   **Filter:** 重点筛选 `status='Pending'` 的工单。
    *   **Action:** 点击“派单”，弹窗或跳转，选择 `sys_user` 中 `role='Worker'` 的用户，更新 `assigned_to` 字段，并将状态改为 `Processing`（或者由维修工接单后改，但通常派单后即视为处理中）。
2.  **库存管理 (Inventory)**
    *   **Route:** `/admin/inventory`
    *   **CRUD:** 对 `spare_part` 表的增删改查。重点是**入库**（增加 `current_stock`）和设置**预警线**。

---

### 第四阶段：维修工端 - 执行与耗材录入 (Worker Module)
这是最复杂的环节，涉及多表事务操作（ACID）。

**功能点：**
1.  **维修任务列表**
    *   **Query:** `RepairOrder.query.filter_by(assigned_to=current_user.id, status='Processing')`。
2.  **维修完工填报 (Finish Repair)**
    *   **Route:** `/worker/finish/<order_id>`
    *   **Form 设计 (难点)**：
        *   **基本信息**：维修结果描述 (`result_desc`)、人工成本 (`labor_cost`)。
        *   **耗材选择 (动态表单)**：利用 JavaScript 添加行，每行包含：下拉框选择配件 (`part_id`) + 输入数量 (`quantity`)。
    *   **后端处理逻辑 (事务安全)**：
        ```python
        try:
            # 1. 创建维修记录 maintenance_record
            record = MaintenanceRecord(order_id=order_id, worker_id=current_user.id, ...)
            db.session.add(record)
            db.session.flush() # 获取 record.id

            # 2. 处理耗材扣减
            for part_item in form_parts_data:
                part = SparePart.query.get(part_item['part_id'])
                if part.current_stock < part_item['quantity']:
                    raise Exception(f"配件 {part.part_name} 库存不足")
                
                # 扣减库存
                part.current_stock -= part_item['quantity']
                
                # 记录明细 (注意 snapshot_price)
                usage = PartUsageDetail(
                    record_id=record.id,
                    part_id=part.id,
                    quantity=part_item['quantity'],
                    snapshot_price=part.price # 重点：记录当前价格快照
                )
                db.session.add(usage)

            # 3. 更新工单状态
            order = RepairOrder.query.get(order_id)
            order.status = 'Finished'
            order.finish_time = datetime.now()

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"提交失败: {str(e)}")
        ```

---

### 第五阶段：报表与看板 (Dashboard & Stats)
根据设计文档的“数据分析”目标。

1.  **管理员仪表盘**
    *   **统计卡片**：待处理工单数、库存预警数、本月维修总成本。
    *   **图表**（使用 Chart.js 或 ECharts）：
        *   故障类型/楼宇分布（饼图）。
        *   维修员工作量排名（柱状图）。
2.  **计算维修成本**
    *   逻辑：`Total Cost = labor_cost + SUM(part_quantity * snapshot_price)`。

---

### 开发顺序建议

1.  **Day 1:** 完成 `base.html` 布局，实现 `@role_required`，完成**库存管理**（因为维修流程依赖配件数据）。
2.  **Day 2:** 完成**学生报修**和**管理员查看列表**（跑通基础数据流）。
3.  **Day 3:** 完成**管理员派单**功能。
4.  **Day 4 (核心难点):** 完成**维修工完工录入**，重点调试库存扣减和事务处理。
5.  **Day 5:** 完成**评价**、**仪表盘图表**以及UI美化。

### 关键提示

*   **ACID 特性**：设计文档特意强调了 MySQL 的 InnoDB 引擎，在写“维修完工”逻辑时，务必把所有数据库操作（写记录、扣库存、改状态）放在同一个 `try...commit...rollback` 块中。
*   **价格快照**：在 `PartUsageDetail` 模型中，写入数据时不要直接关联 `part.price`，而是必须把当前的 `part.price` 赋值给 `snapshot_price`，否则未来配件涨价，历史维修成本计算就会出错。

你可以先从**第三阶段的“库存管理”**开始做，因为这是维修执行的前置条件。是否需要我提供某个具体模块（如维修事务处理）的代码模板？