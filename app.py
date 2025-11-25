"""
Flask 应用主文件
宿舍报修与设备维护管理系统 (TDRM)
"""
import os
from flask import Flask

# 导入配置
from config import config

# 导入扩展初始化函数
from extensions import init_extensions


def create_app(config_name=None):
    """
    应用工厂函数
    创建并配置 Flask 应用实例
    
    参数:
        config_name: 配置名称 ('development', 'production', 'testing')
                     如果为 None，则从环境变量 FLASK_ENV 读取，默认为 'development'
    
    返回:
        Flask 应用实例
    """
    # 创建 Flask 应用实例
    app = Flask(__name__)
    
    # 选择配置
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化扩展（数据库、登录管理器等）
    init_extensions(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理（可选，后续可以添加）
    # register_error_handlers(app)
    
    return app


def register_blueprints(app):
    """
    注册所有蓝图
    
    参数:
        app: Flask 应用实例
    """
    # 导入蓝图
    from blueprints.auth import bp as auth_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.student import bp as student_bp
    from blueprints.worker import bp as worker_bp
    
    # 注册认证蓝图（URL 前缀：/auth）
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # 注册管理员蓝图（URL 前缀：/admin）
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # 注册学生蓝图（URL 前缀：/student）
    app.register_blueprint(student_bp, url_prefix='/student')
    
    # 注册维修人员蓝图（URL 前缀：/worker）
    app.register_blueprint(worker_bp, url_prefix='/worker')


# 创建应用实例（用于直接运行）
app = create_app()

# 根路由
@app.route('/')
def index():
    """首页"""
    return {
        'message': '宿舍报修与设备维护管理系统 (TDRM)',
        'version': '1.0.0',
        'endpoints': {
            'auth': '/auth',
            'admin': '/admin',
            'student': '/student',
            'worker': '/worker'
        }
    }


if __name__ == '__main__':
    # 开发环境运行配置
    app.run(
        host='0.0.0.0',  # 允许外部访问
        port=5000,       # 端口
        debug=True       # 调试模式（生产环境应设为 False）
    )

