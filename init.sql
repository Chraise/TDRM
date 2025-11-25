-- 学生宿舍报修与设备维护管理系统 (Dormitory Repair & Maintenance System) 数据库设计

-- 设置数据库字符集和引擎
-- 使用 InnoDB 引擎以支持事务和外键约束
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- 1. 宿舍楼表 (dorm_building)
-- ----------------------------
DROP TABLE IF EXISTS `dorm_building`;
CREATE TABLE `dorm_building` (
  `building_id` INT NOT NULL AUTO_INCREMENT COMMENT '楼宇ID',
  `building_name` VARCHAR(50) NOT NULL COMMENT '楼名 (如：C楼)',
  `location` VARCHAR(100) NULL COMMENT '地理位置',
  `admin_contact` VARCHAR(20) NULL COMMENT '宿管办公室电话',
  PRIMARY KEY (`building_id`)
) ENGINE=InnoDB COMMENT='宿舍楼表';

-- ----------------------------
-- 2. 用户表 (sys_user)
-- ----------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `user_id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` VARCHAR(50) NOT NULL COMMENT '姓名',
  `password` VARCHAR(100) NOT NULL COMMENT '登录密码 (加密存储)',
  `role` ENUM('Student', 'Worker', 'Admin') NOT NULL COMMENT '角色: Student(学生), Worker(维修人员), Admin(管理员/宿管)',
  `contact` VARCHAR(20) NULL COMMENT '联系电话',
  `building_id` INT NULL COMMENT '所属宿舍楼ID',
  `room_no` VARCHAR(10) NULL COMMENT '房间号 (如 302)',
  `status` TINYINT NOT NULL DEFAULT 1 COMMENT '状态: 1-在校/在职, 0-离校/离职',
  PRIMARY KEY (`user_id`),
  KEY `fk_user_building` (`building_id`),
  CONSTRAINT `fk_user_building` FOREIGN KEY (`building_id`) REFERENCES `dorm_building` (`building_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='系统用户表';

-- ----------------------------
-- 3. 设备/配件库存表 (spare_part)
-- ----------------------------
DROP TABLE IF EXISTS `spare_part`;
CREATE TABLE `spare_part` (
  `part_id` INT NOT NULL AUTO_INCREMENT COMMENT '配件ID',
  `part_name` VARCHAR(100) NOT NULL COMMENT '配件名称 (如：LED灯泡)',
  `spec` VARCHAR(50) NULL COMMENT '规格型号',
  `current_stock` INT NOT NULL DEFAULT 0 COMMENT '当前库存量 (核心字段)',
  `unit` VARCHAR(10) NULL COMMENT '单位 (个, 米)',
  `warning_line` INT NOT NULL DEFAULT 10 COMMENT '预警阈值 (低于此值提示补货)',
  PRIMARY KEY (`part_id`)
) ENGINE=InnoDB COMMENT='设备/配件库存表';

-- ----------------------------
-- 4. 报修单表 (repair_order)
-- ----------------------------
DROP TABLE IF EXISTS `repair_order`;
CREATE TABLE `repair_order` (
  `order_id` INT NOT NULL AUTO_INCREMENT COMMENT '报修单ID',
  `submitter_id` INT NOT NULL COMMENT '报修人ID',
  `building_id` INT NOT NULL COMMENT '故障所在楼ID',
  `room_no` VARCHAR(10) NOT NULL COMMENT '故障所在房间号',
  `title` VARCHAR(100) NOT NULL COMMENT '报修主题',
  `description` TEXT NULL COMMENT '详细描述',
  -- 状态流转: Pending(待处理), Assigned(已派单), InProgress(处理中), Completed(已完成), Cancelled(已取消)
  `status` VARCHAR(20) NOT NULL DEFAULT 'Pending' COMMENT '状态',
  `assigned_to` INT NULL COMMENT '被指派的维修员ID',
  `submit_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  `finish_time` DATETIME NULL COMMENT '实际完成时间 (用于计算绩效)',
  PRIMARY KEY (`order_id`),
  KEY `fk_order_submitter` (`submitter_id`),
  KEY `fk_order_building` (`building_id`),
  KEY `fk_order_assigned` (`assigned_to`),
  CONSTRAINT `fk_order_submitter` FOREIGN KEY (`submitter_id`) REFERENCES `sys_user` (`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_order_building` FOREIGN KEY (`building_id`) REFERENCES `dorm_building` (`building_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  -- 维修员ID可以为空，直到被派单
  CONSTRAINT `fk_order_assigned` FOREIGN KEY (`assigned_to`) REFERENCES `sys_user` (`user_id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='报修单表';

-- ----------------------------
-- 5. 维修记录表 (maintenance_record)
-- ----------------------------
DROP TABLE IF EXISTS `maintenance_record`;
CREATE TABLE `maintenance_record` (
  `record_id` INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `order_id` INT NOT NULL COMMENT '关联报修单ID (1:1 关系)',
  `worker_id` INT NOT NULL COMMENT '实际维修人ID',
  `start_time` DATETIME NULL COMMENT '开始维修时间',
  `end_time` DATETIME NULL COMMENT '结束维修时间',
  `result_desc` TEXT NULL COMMENT '维修结果/故障原因分析',
  `labor_cost` DECIMAL(10,2) NULL COMMENT '人工/时间成本估算',
  PRIMARY KEY (`record_id`),
  UNIQUE KEY `uk_record_order` (`order_id`), -- 确保一个报修单只有一条维修记录
  KEY `fk_record_worker` (`worker_id`),
  CONSTRAINT `fk_record_order` FOREIGN KEY (`order_id`) REFERENCES `repair_order` (`order_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_record_worker` FOREIGN KEY (`worker_id`) REFERENCES `sys_user` (`user_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='维修记录表';

-- ----------------------------
-- 6. 配件消耗明细表 (part_usage_detail)
-- ----------------------------
DROP TABLE IF EXISTS `part_usage_detail`;
CREATE TABLE `part_usage_detail` (
  `usage_id` INT NOT NULL AUTO_INCREMENT COMMENT '流水号',
  `record_id` INT NOT NULL COMMENT '关联维修记录ID',
  `part_id` INT NOT NULL COMMENT '关联配件ID',
  `quantity` INT NOT NULL COMMENT '消耗数量',
  PRIMARY KEY (`usage_id`),
  KEY `fk_usage_record` (`record_id`),
  KEY `fk_usage_part` (`part_id`),
  CONSTRAINT `fk_usage_record` FOREIGN KEY (`record_id`) REFERENCES `maintenance_record` (`record_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_usage_part` FOREIGN KEY (`part_id`) REFERENCES `spare_part` (`part_id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='配件消耗明细表';

-- =================================================================================
-- 核心业务逻辑与数据库编程 (Programmability)
-- =================================================================================

-- ----------------------------
-- 1. 触发器 (Trigger): 库存自动扣减与校验 (trg_deduct_stock)
-- ----------------------------
-- 业务场景：当维修人员在“配件消耗明细表”中添加一条记录时，系统应自动从“设备库存表”中扣除对应数量。如果库存不足，应拦截操作。
DELIMITER //

DROP TRIGGER IF EXISTS `trg_deduct_stock`//
CREATE TRIGGER `trg_deduct_stock`
AFTER INSERT ON `part_usage_detail`
FOR EACH ROW
BEGIN
    DECLARE cur_stock INT;

    -- 1. 获取当前库存
    SELECT `current_stock` INTO cur_stock
    FROM `spare_part`
    WHERE `part_id` = NEW.part_id FOR UPDATE; -- 加锁以确保并发安全

    -- 2. 检查库存是否充足
    IF cur_stock < NEW.quantity THEN
        -- 拦截操作并抛出错误
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Inventory shortage for this part!';
    ELSE
        -- 3. 扣减库存
        UPDATE `spare_part`
        SET `current_stock` = `current_stock` - NEW.quantity
        WHERE `part_id` = NEW.part_id;
    END IF;
END //

DELIMITER ;

-- ----------------------------
-- 2. 视图 (View): 维修绩效统计 (view_worker_performance)
-- ----------------------------
-- 业务场景：管理员需要查看每个维修人员的接单量、平均耗时。
DROP VIEW IF EXISTS `view_worker_performance`;
CREATE VIEW `view_worker_performance` AS
SELECT
    u.username AS worker_name,
    COUNT(r.record_id) AS total_orders,
    -- 计算平均维修耗时 (分钟)
    AVG(TIMESTAMPDIFF(MINUTE, r.start_time, r.end_time)) AS avg_repair_minutes,
    -- 计算平均响应耗时 (从报修提交到维修结束的总时长 - 小时)
    AVG(TIMESTAMPDIFF(HOUR, o.submit_time, r.end_time)) AS avg_response_hours
FROM
    sys_user u
JOIN
    maintenance_record r ON u.user_id = r.worker_id
JOIN
    repair_order o ON r.order_id = o.order_id
WHERE
    u.role = 'Worker' AND r.end_time IS NOT NULL -- 只统计已完成的订单
GROUP BY
    u.user_id, u.username;

-- ----------------------------
-- 3. 存储过程 (Stored Procedure): 自动派单 (auto_assign_order)
-- ----------------------------
-- 业务场景：简单的自动派单逻辑，寻找当前手中“Assigned”或“InProgress”状态单子最少的维修员。
DELIMITER //

DROP PROCEDURE IF EXISTS `auto_assign_order`//
CREATE PROCEDURE `auto_assign_order`(IN p_order_id INT)
BEGIN
    DECLARE v_worker_id INT;

    -- 寻找当前未完成任务数最少的维修人员 (角色必须为 Worker)
    SELECT u.user_id INTO v_worker_id
    FROM `sys_user` u
    LEFT JOIN `repair_order` o ON u.user_id = o.assigned_to
        AND o.status IN ('Assigned', 'InProgress') -- 仅统计进行中的任务
    WHERE u.role = 'Worker'
    GROUP BY u.user_id
    ORDER BY COUNT(o.order_id) ASC -- 任务数最少的优先
    LIMIT 1;

    -- 更新报修单
    IF v_worker_id IS NOT NULL THEN
        UPDATE `repair_order`
        SET `assigned_to` = v_worker_id, `status` = 'Assigned'
        WHERE `order_id` = p_order_id AND `status` = 'Pending';
    ELSE
        -- 如果没有可用的维修员，可以选择记录日志或抛出错误
        SIGNAL SQLSTATE '45001'
        SET MESSAGE_TEXT = 'Error: No available workers to assign the order.';
    END IF;
END //

DELIMITER ;


SET FOREIGN_KEY_CHECKS = 1;