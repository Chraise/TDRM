"""
Flask 扩展初始化模块
统一管理所有 Flask 扩展的创建和初始化
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

# ==================== 扩展对象创建 ====================
# 创建扩展对象（延迟初始化模式，不在此处初始化）
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

# ==================== LoginManager 配置 ====================
# 设置登录视图（未登录用户访问受保护页面时跳转的登录页面）
login_manager.login_view = 'auth.login'

# 设置登录提示消息
login_manager.login_message = '请先登录以访问此页面'
login_manager.login_message_category = 'info'

# 设置会话保护级别
# 'basic': 基本保护
# 'strong': 强保护（检测 IP 和 User-Agent 变化）
# None: 禁用保护
login_manager.session_protection = 'strong'


def init_extensions(app):
    """
    初始化所有 Flask 扩展
    
    参数:
        app: Flask 应用实例
    """
    # 初始化 SQLAlchemy
    db.init_app(app)
    
    # 初始化 Flask-Login
    login_manager.init_app(app)
    
    # 初始化 Flask-Migrate（需要在 db 初始化之后）
    migrate.init_app(app, db)
    
    # 配置用户加载器
    # 注意：需要在 models 模块导入后设置，避免循环导入
    # 使用延迟导入的方式
    @login_manager.user_loader
    def load_user(user_id):
        """
        用户加载器回调函数
        当需要从会话中恢复用户时，Flask-Login 会调用此函数
        
        参数:
            user_id: 用户 ID（字符串形式）
        
        返回:
            User 对象或 None
        """
        # 延迟导入，避免循环导入
        from models import User
        # 将字符串 ID 转换为整数并查询用户
        return User.query.get(int(user_id))

