from sqlalchemy import Column, Integer, String, Boolean, Float
from database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="")
    url = Column(String, unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    fetch_cron = Column(String, default="")
    created_at = Column(Integer, default=0)
    updated_at = Column(Integer, default=0)


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String, nullable=False, unique=True, index=True)
    full_path = Column(String, default="/")
    province = Column(String, default="")
    isp = Column(String, default="")
    latency = Column(Float, default=None)
    created_at = Column(Integer, default=0)
    updated_at = Column(Integer, default=0)


class ChannelGroup(Base):
    __tablename__ = "channel_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0)
    visible = Column(Boolean, default=True)
    created_at = Column(Integer, default=0)


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="")
    code = Column(String, unique=True, nullable=False, index=True)  # 9位数字CODE
    logo = Column(String, default="")  # 台标（URL 或名称）
    group_id = Column(Integer, nullable=False, default=0)
    created_at = Column(Integer, default=0)


class ChannelPlayUrl(Base):
    __tablename__ = "channel_play_urls"

    id = Column(Integer, primary_key=True, index=True)
    channel_code = Column(String, unique=True, nullable=False, index=True)
    play_url = Column(String, nullable=False)
    ttl = Column(Integer, nullable=False, default=0)  # 过期时间戳
    created_at = Column(Integer, default=0)

