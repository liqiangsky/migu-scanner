from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings
import os

# 确保数据目录存在
os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库，删除旧表并重建"""
    conn = engine.connect()
    
    # 删除旧表
    conn.execute(text("DROP TABLE IF EXISTS hosts"))
    conn.execute(text("DROP TABLE IF EXISTS subscriptions"))
    conn.commit()
    
    # 创建新表
    Base.metadata.create_all(bind=engine)
    
    print("Database tables recreated")
