# TDRM - 清华宿舍报修管理系统

## 项目简介

TDRM (Tsinghua Dormitory Repair Management System) 是一个基于 Flask 和 MySQL 的宿舍报修管理平台。系统支持学生提交报修单、维修工接单处理、管理员调度分配和库存管理等功能。

## 技术栈

- **后端框架**: Python 3.11 + Flask
- **ORM**: SQLAlchemy 2.0 (Modern Style)
- **数据库**: MySQL 8.0 (运行在 Docker 中)
- **容器化**: Docker & Docker Compose
- **WSGI 服务器**: Gunicorn
- **前端**: Bootstrap + Jinja2 模板引擎
- **数据填充**: Faker (用于生成测试数据)

## 环境搭建

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 启动步骤

1. 克隆项目
```bash
git clone https://github.com/Chraise/TDRM.git
```

2. 配置环境变量（可选）

项目使用环境变量进行配置，主要配置项包括：
- `WEB_PORT`: Web 服务端口（默认 5000，建议改为 5001）
- `MYSQL_ROOT_PASSWORD`: MySQL root 密码
- `MYSQL_USER`: MySQL 用户（默认 tdrm_user）
- `MYSQL_PASSWORD`: MySQL 密码
- `SECRET_KEY`: Flask 密钥

如果使用默认配置，可直接跳过此步骤。如需自定义，创建 `.env` 文件并设置相应变量。

3. 启动服务

```bash
docker-compose up -d --build
```

首次启动会自动执行数据库迁移。等待容器启动完成后，访问 `http://localhost:5001`（如果修改了 `WEB_PORT`，请使用对应端口）。

**注意**: 由于 macOS 的 AirPlay 服务会占用 5000 端口，建议将 `WEB_PORT` 设置为 5001 或其他端口。

### 验证部署

检查容器状态：
```bash
docker-compose ps
```

查看 Web 服务日志：
```bash
docker logs -f tdrm_web
```

## 数据初始化

项目提供了 `seed.py` 脚本用于生成测试数据。该脚本基于 Faker 生成符合清华真实场景的数据，包括：

- 6 栋宿舍楼（紫荆公寓、南区宿舍等）
- 80 名学生用户（10 位学号格式：年份 + 院系代码 + 4 位随机数）
- 5 名维修工（工号格式：2020990001-2020990005）
- 7 种常见维修配件
- 150 条报修单记录（包含不同状态和完成情况）

### 执行数据填充

进入 Web 容器并运行脚本：

```bash
docker exec -it tdrm_web /bin/bash
flask db upgrade  # 确保数据库表结构最新
python seed.py    # 执行数据填充
```

脚本会自动清理旧数据并生成新的测试数据。执行完成后会输出创建的用户账号信息。

## 测试账号

| 角色 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 管理员 | `admin` | `admin123` | 系统管理员账号 |
| 维修工 | `2020990001` | `123456` | 维修工账号（工号范围：2020990001-2020990005） |
| 学生 | `202x01xxxx` | `123456` | 学生账号为随机生成的 10 位学号，执行 `seed.py` 后会在控制台输出示例账号，或查询数据库 `sys_user` 表 |

## 常用维护命令

### 查看日志

```bash
# Web 服务日志
docker logs -f tdrm_web

# 数据库服务日志
docker logs -f tdrm_db

# 所有服务日志
docker-compose logs -f
```

### 进入容器

```bash
# 进入 Web 容器
docker exec -it tdrm_web /bin/bash

# 进入数据库容器
docker exec -it tdrm_db mysql -u tdrm_user -p
```

### 数据库操作

```bash
# 执行数据库迁移
docker exec -it tdrm_web flask db upgrade

# 创建新的迁移文件
docker exec -it tdrm_web flask db migrate -m "迁移说明"

# 重置数据库（删除所有数据）
docker exec -it tdrm_web python seed.py
```

### 重置环境

```bash
# 停止并删除容器、网络（保留数据卷）
docker-compose down

# 停止并删除容器、网络、数据卷（完全重置）
docker-compose down -v

# 重新构建并启动
docker-compose up -d --build
```

### 其他操作

```bash
# 重启服务
docker-compose restart

# 停止服务
docker-compose stop

# 启动服务
docker-compose start
```

## 项目结构

```
TDRM/
├── app/                    # 应用主目录
│   ├── admin/             # 管理员模块
│   ├── auth/              # 认证模块
│   ├── student/           # 学生模块
│   ├── worker/            # 维修工模块
│   ├── models.py          # 数据模型
│   ├── static/            # 静态资源
│   └── templates/         # 模板文件
├── migrations/             # 数据库迁移文件
├── scripts_for_tests/     # 测试脚本
├── config.py              # 配置文件
├── seed.py                # 数据填充脚本
├── TDRM.py                # 应用入口
├── docker-compose.yml     # Docker Compose 配置
├── Dockerfile             # Docker 镜像构建文件
└── requirements.txt       # Python 依赖
```

## 开发说明

项目使用 SQLAlchemy 2.0 的 Modern Style API，所有模型定义采用类型注解和 `Mapped` 类型。数据库迁移使用 Flask-Migrate (Alembic) 管理。

如需本地开发（不使用 Docker），需要：
1. 安装 Python 3.11+
2. 安装 MySQL 8.0
3. 创建虚拟环境并安装依赖：`pip install -r requirements.txt`
4. 配置 `.env` 文件或设置环境变量
5. 执行 `flask db upgrade` 初始化数据库
6. 运行 `python seed.py` 填充测试数据
7. 使用 `flask run` 启动开发服务器

## 许可证

详见 [LICENSE](LICENSE) 文件。
