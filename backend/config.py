from pydantic_settings import BaseSettings
from pathlib import Path
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 上海时区
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def now_shanghai() -> datetime:
    """获取上海时区的当前时间"""
    return datetime.now(SHANGHAI_TZ)


def timestamp_shanghai() -> int:
    """获取上海时区的当前时间戳"""
    return int(datetime.now(SHANGHAI_TZ).timestamp())


class Settings(BaseSettings):
    # 数据库
    db_path: str = str(Path(__file__).parent / "data" / "migu.db")

    # ip2region 数据库路径
    ip2region_db: str = str(Path(__file__).parent / "data" / "ip2region_v4.xdb")

    # 超时配置
    request_timeout: int = 30
    latency_timeout: int = 5

    class Config:
        env_prefix = "MIGU_"
        env_file = ".env"


settings = Settings()
