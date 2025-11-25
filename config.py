"""
配置文件
支持开发环境和生产环境的配置

使用说明：
直接修改下面的配置值即可，无需设置环境变量
"""
from datetime import timedelta


class Config:
    """基础配置类"""
    # Flask 应用配置
    # 请修改为你的密钥（生产环境请使用强随机字符串）
    SECRET_KEY = 'dev-secret-key-change-in-production'
    
    # ==================== 数据库配置 ====================
    # 请根据你的实际情况修改以下配置
    MYSQL_HOST = 'localhost'       # MySQL 服务器地址
    MYSQL_PORT = 3306              # MySQL 端口
    MYSQL_USER = 'root'            # MySQL 用户名
    MYSQL_PASSWORD = 'root123456'  # MySQL 密码（请修改为你的密码）
    MYSQL_DATABASE = 'tdrm'        # 数据库名称
    # ====================================================
    
    # SQLAlchemy 配置
    # 注意：这里使用 f-string 在类定义时求值
    # 如果修改了上面的数据库配置，URI 会自动更新
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 是否打印 SQL 语句，开发时可设为 True
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 会话有效期 7 天
    SESSION_COOKIE_SECURE = False  # 生产环境使用 HTTPS 时应设为 True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 分页配置
    ITEMS_PER_PAGE = 20  # 每页显示的项目数


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True  # 开发环境打印 SQL 语句


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True  # 生产环境需要 HTTPS
    
    # 生产环境请务必修改 SECRET_KEY 为强随机字符串
    # 可以使用以下命令生成：python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY = 'CHANGE-THIS-TO-A-SECURE-RANDOM-STRING-IN-PRODUCTION'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 测试使用内存数据库
    WTF_CSRF_ENABLED = False  # 测试时禁用 CSRF


# 配置字典，方便根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

