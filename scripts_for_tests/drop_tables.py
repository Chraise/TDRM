"""
删除数据库所有表脚本
删除所有表，但保留数据库
"""
from app import create_app, db
from sqlalchemy import inspect, text


def drop_tables():
    """删除所有表，但保留数据库"""
    app = create_app()
    
    with app.app_context():
        try:
            # 获取数据库连接
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if not tables:
                print("数据库中没有任何表")
                return
            
            print(f"发现 {len(tables)} 个表: {', '.join(tables)}")
            
            # 禁用外键检查（SQLite）
            if 'sqlite' in db.engine.url.drivername:
                db.session.execute(text('PRAGMA foreign_keys = OFF'))
            
            # 删除所有表
            db.drop_all()
            db.session.commit()
            
            # 重新启用外键检查
            if 'sqlite' in db.engine.url.drivername:
                db.session.execute(text('PRAGMA foreign_keys = ON'))
            
            print(f"\n✅ 已删除所有 {len(tables)} 个表，数据库已保留")
            print("提示: 如需重新创建表结构，请运行: flask db upgrade")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ 删除表时发生错误: {e}")
            raise


if __name__ == '__main__':
    drop_tables()




