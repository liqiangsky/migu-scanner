"""
通知服务：创建通知并推送到 SSE
"""
import logging
import asyncio
from sqlalchemy.orm import Session
from config import timestamp_shanghai

logger = logging.getLogger("通知服务")

MSG_TYPE_SUCCESS = "success"
MSG_TYPE_ERROR = "error"
MSG_TYPE_INFO = "info"


def create_notification(db: Session, msg_type: str, title: str, content: str = "", source: str = ""):
    """创建通知并推送到 SSE"""
    now = timestamp_shanghai()
    logger.info(f"📬 [通知] [{msg_type}] {title}")
    _publish_async(msg_type, {
        "type": msg_type,
        "title": title,
        "content": content,
        "source": source,
        "createdAt": now,
    })


def _publish_async(event_type: str, data: dict):
    """在非 async 上下文中安全地发布事件"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            from services.event_bus import event_bus
            asyncio.create_task(event_bus.publish(event_type, data))
    except RuntimeError:
        pass
