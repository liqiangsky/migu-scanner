"""
数据库初始化 - 创建所有表
"""

from database import engine, Base
from models import Subscription, Host, ChannelGroup, Channel, ChannelPlayUrl


def init_db():
    """创建所有表（如果不存在）"""
    Base.metadata.create_all(bind=engine)
