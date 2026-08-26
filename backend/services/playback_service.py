import logging
import random
import time
import requests
from typing import Optional
from sqlalchemy.orm import Session

from config import settings
from models import Host, ChannelPlayUrl
from database import db_write_lock

logger = logging.getLogger("migu.playback")


def resolve_play_url(db: Session, channel_code: str) -> str:
    """
    获取频道播放URL：
    1. 先从缓存表查找未过期的URL
    2. 缓存未命中，从主机池随机选取主机
    3. 逐一尝试获取播放URL，首个成功则写入缓存并返回
    4. 请求失败的主机跳过，继续尝试下一个
    5. 全部失败则抛异常
    """
    # 先查缓存
    cached = db.query(ChannelPlayUrl).filter(
        ChannelPlayUrl.channel_code == channel_code,
        ChannelPlayUrl.ttl > int(time.time())
    ).first()
    if cached:
        logger.info(f"频道 {channel_code} 使用缓存URL: {cached.play_url[:80]}...")
        return cached.play_url

    # 获取主机列表，随机排序
    hosts = db.query(Host).all()
    random.shuffle(hosts)

    if not hosts:
        logger.warning(f"频道 {channel_code} 无可用的主机节点")
        raise Exception("暂无可用主机节点")

    logger.info(
        f"频道 {channel_code} 开始从 {len(hosts)} 个主机节点获取播放URL"
    )

    # 遍历主机，逐个尝试
    for i, host in enumerate(hosts):
        logger.debug(
            f"频道 {channel_code} 尝试主机 [{i+1}/{len(hosts)}]: "
            f"{host.host} (latency={host.latency}ms)"
        )
        try:
            play_url = _get_play_url(host, channel_code)

            if play_url:
                logger.info(
                    f"频道 {channel_code} 从主机 {host.host} 获取到播放URL: {play_url[:80]}..."
                )
                _save_play_url(db, channel_code, play_url)
                return play_url
            else:
                logger.warning(f"频道 {channel_code} 主机 {host.host} 返回空URL，跳过该主机")
        except Exception as e:
            logger.warning(f"频道 {channel_code} 主机 {host.host} 请求失败: {e}，跳过该主机")

    # 全部失败
    raise Exception(f"频道 {channel_code} 暂无可用播放源")


def _save_play_url(db: Session, channel_code: str, play_url: str):
    """保存播放URL到缓存表"""
    ttl = int(time.time()) + settings.playback_cache_ttl
    existing = db.query(ChannelPlayUrl).filter(
        ChannelPlayUrl.channel_code == channel_code
    ).first()
    if existing:
        existing.play_url = play_url
        existing.ttl = ttl
    else:
        with db_write_lock:
            db.add(ChannelPlayUrl(
                channel_code=channel_code,
                play_url=play_url,
                ttl=ttl,
                created_at=int(time.time())
            ))
    with db_write_lock:
        db.commit()
    logger.debug(f"频道 {channel_code} 播放URL已缓存，TTL={settings.playback_cache_ttl}s")


def _get_play_url(host: Host, channel_code: str) -> Optional[str]:
    """
    同步方式请求主机获取频道播放URL。
    主机返回302跳转链，最终响应URL即为m3u8播放地址。
    """
    test_url = f"{host.full_path.rstrip('/')}/{channel_code}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        resp = requests.get(
            test_url,
            headers=headers,
            timeout=settings.playback_request_timeout,
            allow_redirects=True
        )

        # 最终URL即为播放URL（302跳转链终点）
        final_url = resp.url
        if final_url and isinstance(final_url, str):
            # 验证是合法的播放URL
            if any(ext in final_url.lower() for ext in ['.m3u8', '.flv']):
                return final_url
            # 也接受包含 miguvideo 的URL
            if 'miguvideo' in final_url.lower():
                return final_url

        return None
    except requests.exceptions.RequestException:
        return None
