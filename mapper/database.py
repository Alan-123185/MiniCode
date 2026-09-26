import sqlite3  # 导入 sqlite3 模块，用于与 SQLite 数据库通信
from config.data import settings


class DataBase:  # 定义 DataBase 类，封装数据库操作
    """数据库操作类"""

    def __init__(self):  # 构造函数，允许传入数据库文件路径，默认为 minicodexdatabase.db
        self.conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)  # 创建数据库连接，关闭同线程检查以支持多线程访问
        self.conn.row_factory = sqlite3.Row  # 将行工厂设置为 sqlite3.Row，以便可以像字典一样通过列名访问结果
        self.conn.execute("PRAGMA journal_mode=WAL;")  # 设置 WAL 模式以提高并发性能

    def _init_tables(self):  # 私有方法：创建所需的表（如果不存在）
        # 使用 executescript 执行多条 SQL 语句（此处使用多行字符串包含 SQL）
        with open(settings.sql_script_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        self.conn.executescript(sql_content)  # 执行 SQL 脚本来确保表存在

    def execute(self, sql, params=()):  # 通用的执行方法，用于 INSERT/UPDATE/DELETE，返回最后插入行的 id
        try:  # 尝试执行并提交事务
            cur = self.conn.cursor()  # 获取游标对象以执行 SQL
            cur.execute(sql, params)  # 执行 SQL 语句并绑定参数
            self.conn.commit()  # 提交事务以保存更改
            return cur.lastrowid  # 返回最后插入行的 ID（如果适用）
        except Exception as e:  # 捕获所有异常以便回滚事务并向上抛出错误
            self.conn.rollback()  # 出现错误时回滚事务以保持数据库一致性
            raise e  # 重新抛出异常以便调用者处理

    def fetch_all(self, sql, params=()):  # 执行查询并返回所有匹配行，结果为字典列表
        cur = self.conn.cursor()  # 获取游标
        cur.execute(sql, params)  # 执行查询语句并传入参数
        return [dict(r) for r in cur.fetchall()]  # 将 sqlite3.Row 对象转换为字典并返回列表

    def fetch_one(self, sql, params=()):  # 执行查询并返回单条记录（字典形式）或 None
        cur = self.conn.cursor()  # 获取游标对象
        cur.execute(sql, params)  # 执行 SQL 查询
        row = cur.fetchone()  # 获取第一条结果
        return dict(row) if row else None  # 如果有结果则转换为字典，否则返回 None



def init_tables() -> None:
    """进程启动时由 lifespan 调用，整个进程只跑一次"""
    db = DataBase()
    try:
        db._init_tables()
    finally:
        db.conn.close()















# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,async_sessionmaker
# from sqlalchemy.orm import declarative_base
#
# from config.data import settings
#
# # 1. 创建 engine（连接池）
# engine = create_async_engine(settings.async_database_url, echo=False)
#
# # 2. 创建 sessionmaker 工厂
# async_session = async_sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False
# )
#
# Base = declarative_base()
# # 3. (可选) 提供一个给 FastAPI 用的依赖函数
# async def get_db():
#     async with async_session() as session:
#         yield session