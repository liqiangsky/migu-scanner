from pydantic_settings import BaseSettings
from pathlib import Path
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# 上海时区
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


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

    # 播放代理配置
    playback_request_timeout: int = 10  # 单个主机尝试超时（秒）
    playback_cache_ttl: int = 18000  # 播放URL缓存时间（秒），默认5小时

    # 拉取并发配置
    max_concurrent_subscriptions: int = 5  # 最多同时拉取的订阅数
    max_concurrent_hosts_per_subscription: int = 10  # 每个订阅最多同时验证的HOST数

    class Config:
        env_prefix = "MIGU_"
        env_file = ".env"


settings = Settings()
