-- ==========================================================
-- 宿舍报修系统数据库定义脚本
-- ==========================================================

-- 1. 创建宿舍楼表
CREATE TABLE dorm_building (
    building_id SERIAL PRIMARY KEY,
    building_name VARCHAR(50) NOT NULL UNIQUE,
    location VARCHAR(100),
    admin_contact VARCHAR(20),
    CONSTRAINT ix_dorm_building_building_name INDEX (building_name)
);

-- 2. 创建用户表 (sys_user)
CREATE TABLE sys_user (
    user_id SERIAL PRIMARY KEY,
    account VARCHAR(50) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL,
    password VARCHAR(256) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 存储枚举值: Student, Worker, Admin
    email VARCHAR(120) NOT NULL UNIQUE,
    building_id INTEGER,
    room_no VARCHAR(10),
    status SMALLINT DEFAULT 1, -- 1-在校/在职, 0-离校/离职
    FOREIGN KEY (building_id) REFERENCES dorm_building(building_id) ON DELETE SET NULL ON UPDATE CASCADE
);
CREATE INDEX ix_sys_user_account ON sys_user(account);
CREATE INDEX ix_sys_user_username ON sys_user(username);
CREATE INDEX ix_sys_user_role ON sys_user(role);
CREATE INDEX ix_sys_user_email ON sys_user(email);
CREATE INDEX ix_sys_user_status ON sys_user(status);

-- 3. 创建配件库存表
CREATE TABLE spare_part (
    part_id SERIAL PRIMARY KEY,
    part_name VARCHAR(100) NOT NULL,
    spec VARCHAR(50),
    current_stock INTEGER NOT NULL DEFAULT 0,
    unit VARCHAR(10),
    warning_line INTEGER NOT NULL DEFAULT 10,
    price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT uq_part_name_spec UNIQUE (part_name, spec),
    CONSTRAINT ck_stock_non_negative CHECK (current_stock >= 0)
);
CREATE INDEX ix_spare_part_part_name ON spare_part(part_name);

-- 4. 创建报修单表
CREATE TABLE repair_order (
    order_id SERIAL PRIMARY KEY,
    submitter_id INTEGER NOT NULL,
    repair_building_id INTEGER NOT NULL,
    repair_location VARCHAR(10) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    image_urls TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending', -- 存储枚举值
    submit_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finish_time TIMESTAMP WITH TIME ZONE,
    rating SMALLINT,
    feedback VARCHAR(255),
    FOREIGN KEY (submitter_id) REFERENCES sys_user(user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (repair_building_id) REFERENCES dorm_building(building_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 5. 创建报修单与维修工的多对多关联表 (派单中间表)
CREATE TABLE order_assign (
    user_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, order_id),
    FOREIGN KEY (user_id) REFERENCES sys_user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES repair_order(order_id) ON DELETE CASCADE
);

-- 6. 创建维修记录表
CREATE TABLE maintenance_record (
    record_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    result_desc TEXT,
    labor_cost NUMERIC(10, 2),
    FOREIGN KEY (order_id) REFERENCES repair_order(order_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES sys_user(user_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- 7. 创建配件消耗明细表
CREATE TABLE part_usage_detail (
    usage_id SERIAL PRIMARY KEY,
    record_id INTEGER NOT NULL,
    part_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (record_id) REFERENCES maintenance_record(record_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (part_id) REFERENCES spare_part(part_id) ON DELETE RESTRICT ON UPDATE CASCADE
);