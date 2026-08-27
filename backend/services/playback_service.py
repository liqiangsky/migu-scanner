import logging
import random
import time
import requests
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from config import settings
from models import Host, ChannelPlayUrl
from database import db_write_lock

logger = logging.getLogger("migu.playback")

# _get_play_url 返回值状态
RESULT_OK = "ok"          # 成功获取播放URL
RESULT_HOST_ERROR = "host_error"   # 主机请求失败（超时/网络错误），应标记无效
RESULT_CHANNEL_UNAVAIL = "channel_unavail"  # 主机正常，但该频道无播放URL


def _mark_host_invalid(db: Session, host: Host):
    """标记主机为无效：更新 latency=-1 和 updated_at"""
    if host.latency < 0:
        return  # 已经是无效状态，无需重复更新
    host.latency = -1
    host.updated_at = int(time.time())
    with db_write_lock:
        db.commit()
    logger.warning(f"主机 {host.host} 播放失败，已标记为无效")


def resolve_play_url(db: Session, channel_code: str) -> str:
    """
    获取频道播放URL：
    1. 先从缓存表查找未过期的URL
    2. 缓存未命中，从主机池随机选取主机（排除已标记无效的主机）
    3. 逐一尝试获取播放URL，首个成功则写入缓存并返回
    4. 主机请求失败（超时/网络错误）才标记无效并跳过；频道不可用仅跳过
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

    # 获取有效主机列表（latency >= 0），随机排序
    hosts = db.query(Host).filter(Host.latency >= 0).all()
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
            result, play_url = _get_play_url(host, channel_code)

            if result == RESULT_OK:
                logger.info(
                    f"频道 {channel_code} 从主机 {host.host} 获取到播放URL: {play_url[:80]}..."
                )
                _save_play_url(db, channel_code, play_url)
                return play_url
            elif result == RESULT_HOST_ERROR:
                logger.warning(f"频道 {channel_code} 主机 {host.host} 请求失败，标记无效并跳过")
                _mark_host_invalid(db, host)
            else:
                # RESULT_CHANNEL_UNAVAIL：主机正常，该频道不可用，跳过
                logger.debug(f"频道 {channel_code} 在主机 {host.host} 上不可用，尝试下一个")

        except Exception as e:
            logger.warning(f"频道 {channel_code} 主机 {host.host} 请求失败: {e}，标记无效并跳过")
            _mark_host_invalid(db, host)

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


def _get_play_url(host: Host, channel_code: str) -> Tuple[str, Optional[str]]:
    """
    同步方式请求主机获取频道播放URL。
    返回 (result, play_url)，result 为 RESULT_OK / RESULT_HOST_ERROR / RESULT_CHANNEL_UNAVAIL。
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
                return RESULT_OK, final_url
            # 也接受包含 miguvideo 的URL
            if 'miguvideo' in final_url.lower():
                return RESULT_OK, final_url

        # 请求成功但返回非视频URL（频道在此主机不可用）
        return RESULT_CHANNEL_UNAVAIL, None

    except requests.exceptions.Timeout:
        logger.warning(f"主机 {host.host} 请求超时")
        return RESULT_HOST_ERROR, None
    except requests.exceptions.RequestException as e:
        logger.warning(f"主机 {host.host} 请求异常: {e}")
        return RESULT_HOST_ERROR, None
