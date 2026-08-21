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
    host = Column(String, nullable=False, index=True)
    full_path = Column(String, default="/")
    province = Column(String, default="")
    isp = Column(String, default="")
    latency = Column(Float, default=None)
    created_at = Column(Integer, default=0)
    updated_at = Column(Integer, default=0)
