import json
import os
import logging
from typing import Dict, Any
from config import settings

logger = logging.getLogger("migu.settings")

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "settings.json")


def load_settings() -> Dict[str, Any]:
    """从文件加载设置"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载设置文件失败: {e}")
    return {}


def save_settings(data: Dict[str, Any]) -> bool:
    """保存设置到文件"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"保存设置文件失败: {e}")
        return False


def get_all_settings() -> Dict[str, Any]:
    """获取所有设置（合并默认值和自定义值）"""
    saved = load_settings()
    defaults = {
        "max_concurrent_subscriptions": settings.max_concurrent_subscriptions,
        "max_concurrent_hosts_per_subscription": settings.max_concurrent_hosts_per_subscription,
        "request_timeout": settings.request_timeout,
        "latency_timeout": settings.latency_timeout,
        "playback_request_timeout": settings.playback_request_timeout,
        "playback_cache_ttl": settings.playback_cache_ttl,
    }
    # 合并：自定义值优先于默认值
    merged = {**defaults, **saved}
    return merged


def update_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """更新设置"""
    allowed_keys = {
        "max_concurrent_subscriptions",
        "max_concurrent_hosts_per_subscription",
        "request_timeout",
        "latency_timeout",
        "playback_request_timeout",
        "playback_cache_ttl",
    }
    
    # 过滤只允许更新的键
    filtered = {k: v for k, v in data.items() if k in allowed_keys}
    
    if filtered:
        saved = load_settings()
        saved.update(filtered)
        if save_settings(saved):
            logger.info(f"设置已更新: {filtered}")
            return get_all_settings()
    
    return get_all_settings()


# 定义设置项的元数据（用于前端显示）
SETTINGS_METADATA = [
    {
        "key": "max_concurrent_subscriptions",
        "label": "同时拉取的订阅数",
        "description": "批量拉取时，最多同时运行的订阅拉取任务数",
        "type": "number",
        "min": 1,
        "max": 50,
        "default": 5,
    },
    {
        "key": "max_concurrent_hosts_per_subscription",
        "label": "每订阅最大并发验证数",
        "description": "每个订阅内，最多同时验证的 HOST 数量",
        "type": "number",
        "min": 1,
        "max": 50,
        "default": 10,
    },
    {
        "key": "request_timeout",
        "label": "订阅源请求超时（秒）",
        "description": "拉取订阅源时的 HTTP 请求超时时间",
        "type": "number",
        "min": 5,
        "max": 120,
        "default": 30,
    },
    {
        "key": "latency_timeout",
        "label": "HOST 验证超时（秒）",
        "description": "验证单个 HOST 时的响应超时时间",
        "type": "number",
        "min": 1,
        "max": 30,
        "default": 5,
    },
    {
        "key": "playback_request_timeout",
        "label": "播放代理超时（秒）",
        "description": "播放频道时的单个主机尝试超时时间",
        "type": "number",
        "min": 5,
        "max": 60,
        "default": 10,
    },
    {
        "key": "playback_cache_ttl",
        "label": "播放缓存时间（秒）",
        "description": "播放 URL 的缓存有效期",
        "type": "number",
        "min": 600,
        "max": 86400,
        "default": 18000,
    },
]
