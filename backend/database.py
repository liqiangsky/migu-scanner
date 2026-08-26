from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os
import shutil
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# 确保数据目录存在
os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 全局 SQLite 写锁：序列化所有并发写入，防止 database is locked
db_write_lock = threading.Lock()


# ============ SQLite 防护配置 ============

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """设置 SQLite 安全相关 pragmas"""
    cursor = dbapi_connection.cursor()
    try:
        # WAL 模式：允许读写并发，崩溃恢复更安全，防止 CORRUPT
        cursor.execute("PRAGMA journal_mode = WAL")
        # 同步模式：NORMAL 平衡性能与安全（FULL 最安全但慢，WAL模式下NORMAL足够）
        cursor.execute("PRAGMA synchronous = NORMAL")
        # 临时表存储在内存中，减少磁盘I/O
        cursor.execute("PRAGMA temp_store = MEMORY")
        # 启用外键约束
        cursor.execute("PRAGMA foreign_keys = ON")
        # 增加写操作超时（30秒），避免并发写入时立刻失败
        cursor.execute("PRAGMA busy_timeout = 30000")
        logger.debug("SQLite pragmas 设置完成: journal_mode=WAL, synchronous=NORMAL")
    except Exception as e:
        logger.error(f"设置 SQLite pragmas 失败: {e}")
    finally:
        cursor.close()


# 捕获所有 SQL 错误，记录详细日志便于排查
@event.listens_for(engine, "handle_error")
def handle_error(exception_context):
    """全局错误处理：记录 SQLite 错误详情"""
    err = exception_context.original_exception
    if err:
        msg = str(err)
        if "CORRUPT" in msg or "malformed" in msg.lower():
            logger.error(f"数据库损坏检测: {msg}")
        elif "database is locked" in msg.lower():
            logger.warning(f"数据库锁冲突（可自动重试）: {msg}")
        else:
            logger.debug(f"SQL 错误: {msg}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_integrity() -> bool:
    """检查数据库完整性，返回 True 表示正常"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA integrity_check")).fetchone()
            if result[0] == "ok":
                logger.debug("数据库完整性检查通过")
                return True
            else:
                logger.error(f"数据库完整性检查失败: {result[0]}")
                return False
    except Exception as e:
        logger.error(f"数据库完整性检查异常: {e}")
        return False


def periodic_maintenance():
    """定期维护任务（仅做完整性检查，不做 VACUUM）"""
    while True:
        time.sleep(3600)  # 每小时
        try:
            check_integrity()
        except Exception as e:
            logger.error(f"定期维护失败: {e}")


def start_maintenance_thread():
    """启动后台维护线程（守护线程，随主进程退出）"""
    t = threading.Thread(target=periodic_maintenance, daemon=True)
    t.start()
    logger.info("数据库维护线程已启动")


def init_db():
    """创建所有表（如果不存在），并执行数据库健康检查"""
    # 启动后台维护线程
    start_maintenance_thread()

    # 启动时检查数据库完整性
    if not check_integrity():
        logger.warning("启动时数据库完整性检查失败，尝试备份后重建...")
        _backup_and_recover()

    Base.metadata.create_all(bind=engine)
    logger.info("数据库初始化完成")


def _backup_and_recover():
    """备份损坏的数据库并尝试恢复"""
    try:
        db_dir = os.path.dirname(settings.db_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(db_dir, f"migu_backup_{timestamp}.db")

        # 创建备份（即使损坏也保留现场）
        if os.path.exists(settings.db_path):
            shutil.copy2(settings.db_path, backup_path)
            logger.info(f"已创建数据库备份: {backup_path}")

        # 删除损坏的文件，重新初始化
        if os.path.exists(settings.db_path):
            os.remove(settings.db_path)
            # 同时删除 WAL 文件（如果有）
            wal_path = settings.db_path + "-wal"
            shm_path = settings.db_path + "-shm"
            for p in [wal_path, shm_path]:
                if os.path.exists(p):
                    os.remove(p)

        # 重建表结构（数据丢失，需用户重新导入）
        Base.metadata.create_all(bind=engine)
        logger.warning("数据库已重建，原有数据已丢失。请检查备份文件恢复。")
    except Exception as e:
        logger.error(f"数据库恢复失败: {e}", exc_info=True)
