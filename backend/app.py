import asyncio
import re
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, exc

from database import get_db, init_db, SessionLocal, check_integrity, db_write_lock
from models import Subscription, Host, ChannelGroup, Channel, ChannelPlayUrl
from services.notification_service import create_notification, MSG_TYPE_SUCCESS, MSG_TYPE_ERROR
from services.url_parser import parse_all_sources
from services.channel_parser import detect_and_parse, filter_migu_channels, extract_code
from services.host_resolver import get_resolver, TEST_CHANNEL_CODE
from services import playback_service
from config import settings, timestamp_shanghai

import requests

# 配置控制台日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("migu")



app = FastAPI(title="Migu Subscriptions", version="1.0.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("=== 服务器启动 ===")


@app.on_event("shutdown")
async def shutdown_event():
    """优雅关闭：清理数据库连接"""
    from services.event_bus import event_bus
    event_bus.clear_all()
    logger.info("=== 服务器关闭 ===")


# 自定义错误码
class ErrorCode:
    SUCCESS = 200
    PARAM_ERROR = 1001      # 参数错误
    NOT_FOUND = 1002        # 资源不存在
    DUPLICATE = 1003        # 重复
    SERVER_ERROR = 5000     # 服务器错误


def success_response(data=None, msg="success"):
    return {"code": ErrorCode.SUCCESS, "data": data, "msg": msg}


def error_response(msg="error", code=ErrorCode.PARAM_ERROR):
    return {"code": code, "data": None, "msg": msg}


class BusinessException(Exception):
    """业务异常，携带错误码和消息"""
    def __init__(self, message, code=ErrorCode.PARAM_ERROR):
        self.message = message
        self.code = code
        super().__init__(self.message)


@app.exception_handler(BusinessException)
async def business_exception_handler(request, exc):
    return JSONResponse(
        status_code=200,
        content=error_response(msg=exc.message, code=exc.code)
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    # 将 HTTPException 映射到自定义错误码
    code = ErrorCode.PARAM_ERROR if exc.status_code == 400 else ErrorCode.NOT_FOUND
    return JSONResponse(
        status_code=200,
        content=error_response(msg=exc.detail, code=code)
    )


@app.exception_handler(Exception)
async def sqlite_corrupt_handler(request, exc):
    """全局异常处理：检测并友好处理 SQLite 损坏错误"""
    msg = str(exc)
    if "CORRUPT" in msg or "malformed" in msg.lower() or "database disk image is malformed" in msg.lower():
        logger.error(f"检测到数据库损坏: {msg}")
        return JSONResponse(
            status_code=200,
            content=error_response(
                msg="数据库损坏，正在尝试恢复...请稍后再试。如有需要请联系管理员。",
                code=ErrorCode.SERVER_ERROR
            )
        )
    # 其他未处理异常
    logger.error(f"未处理异常: {msg}", exc_info=True)
    return JSONResponse(
        status_code=200,
        content=error_response(msg="服务器内部错误", code=ErrorCode.SERVER_ERROR)
    )


# ============ 订阅管理 API ============

@app.get("/subscriptions")
async def get_subscriptions(db: Session = Depends(get_db)):
    sources = db.query(Subscription).all()
    logger.debug(f"获取订阅列表: {len(sources)} 条")
    return success_response(data=[{
        "id": s.id, "name": s.name or "", "url": s.url,
        "enabled": s.enabled, "fetchCron": s.fetch_cron or "",
        "createdAt": s.created_at, "updatedAt": s.updated_at,
    } for s in sources])


class SubscriptionCreate(BaseModel):
    name: str = ""
    url: str
    fetch_cron: str = ""


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    enabled: Optional[bool] = None
    fetch_cron: Optional[str] = None


@app.post("/subscriptions")
async def add_subscription(body: SubscriptionCreate, db: Session = Depends(get_db)):
    url = body.url.strip()
    logger.info(f"添加订阅请求: name='{body.name}', url='{url}'")
    if not url:
        raise BusinessException("URL不能为空", ErrorCode.PARAM_ERROR)
    existing = db.query(Subscription).filter(Subscription.url == url).first()
    if existing:
        logger.warning(f"添加订阅失败: URL 已存在 {url}")
        raise BusinessException("URL已存在", ErrorCode.DUPLICATE)
    now = timestamp_shanghai()
    source = Subscription(
        name=body.name.strip(), url=url, enabled=True,
        fetch_cron=body.fetch_cron.strip(), created_at=now, updated_at=now
    )
    db.add(source)
    with db_write_lock:
        db.commit()
    logger.info(f"添加订阅成功: ID={source.id}, name='{body.name}', url='{url}'")
    return success_response(data={"id": source.id}, msg="添加成功")


@app.put("/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: int, body: SubscriptionUpdate, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise BusinessException("订阅不存在", ErrorCode.NOT_FOUND)
    logger.info(f"更新订阅: ID={subscription_id}")
    if body.name is not None:
        subscription.name = body.name.strip()
    if body.url is not None:
        url = body.url.strip()
        dup = db.query(Subscription).filter(Subscription.url == url, Subscription.id != subscription_id).first()
        if dup:
            raise BusinessException("URL已存在", ErrorCode.DUPLICATE)
        subscription.url = url
    if body.enabled is not None:
        subscription.enabled = body.enabled
    if body.fetch_cron is not None:
        subscription.fetch_cron = body.fetch_cron.strip()
    subscription.updated_at = timestamp_shanghai()
    with db_write_lock:
        db.commit()
    logger.info(f"更新订阅成功: ID={subscription_id}")
    return success_response(msg="更新成功")


@app.delete("/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise BusinessException("订阅不存在", ErrorCode.NOT_FOUND)
    logger.info(f"删除订阅: ID={subscription_id}, url={subscription.url}")
    with db_write_lock:
        db.delete(subscription)
        db.commit()
    logger.info(f"删除订阅成功: ID={subscription_id}")
    return success_response(msg="删除成功")


# ============ HOST 管理 API ============

@app.get("/hosts")
async def get_hosts(
    page: int = Query(1),
    page_size: int = Query(20),
    province: str = Query(""),
    isp: str = Query(""),
    db: Session = Depends(get_db)
):
    """获取主机列表（分页+筛选）"""
    query = db.query(Host)

    # 筛选条件
    if province:
        query = query.filter(Host.province == province)
    if isp:
        query = query.filter(Host.isp == isp)

    # 总数
    total = query.count()

    # 分页
    if page < 1:
        page = 1
    page_size = max(1, min(page_size, 200))
    offset = (page - 1) * page_size

    hosts = query.order_by(Host.created_at.desc()).offset(offset).limit(page_size).all()

    return success_response(data={
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": (total + page_size - 1) // page_size,
        "items": [{
            "id": h.id, "host": h.host, "full_path": h.full_path, "province": h.province,
            "isp": h.isp, "latency": h.latency,
            "createdAt": h.created_at, "updatedAt": h.updated_at,
        } for h in hosts]
    })


@app.get("/hosts/filters")
async def get_host_filters(db: Session = Depends(get_db)):
    """获取筛选选项（地区和运营商的去重列表）"""
    from sqlalchemy import distinct
    province_list = db.query(distinct(Host.province)).filter(Host.province != "").all()
    isp_list = db.query(distinct(Host.isp)).filter(Host.isp != "").all()
    provinces = [row[0] for row in province_list if row[0]]
    isps = [row[0] for row in isp_list if row[0]]
    return success_response(data={"provinces": provinces, "isps": isps})


@app.delete("/hosts/{host_id}")
async def delete_host(host_id: int, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise BusinessException("主机不存在", ErrorCode.NOT_FOUND)
    logger.info(f"删除主机: ID={host_id}, host={host.host}")
    with db_write_lock:
        db.delete(host)
        db.commit()
    logger.info(f"删除主机成功: ID={host_id}")
    return success_response(msg="删除成功")


@app.post("/hosts/{host_id}/test-delay")
async def test_host_delay(host_id: int, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise BusinessException("主机不存在", ErrorCode.NOT_FOUND)

    resolver = get_resolver()
    # 直接从 full_path 拼接 TEST_CHANNEL_CODE
    test_url = f"{host.full_path.rstrip('/')}/{TEST_CHANNEL_CODE}"
    result = await resolver.test_host(test_url)
    latency = result.get("latency", -1)

    host.latency = latency
    host.updated_at = timestamp_shanghai()
    with db_write_lock:
        db.commit()

    return success_response(data={
        "delay": latency,
        "updatedAt": host.updated_at
    }, msg="success")


# ============ 拉取 API ============

async def _pull_subscription(subscription_id: int):
    """核心拉取逻辑，供单订阅和批量拉取复用。使用独立 DB session。"""
    added = 0
    skipped = 0
    errors = []
    # 后台任务使用独立 session，不依赖请求级 session
    db = SessionLocal()
    try:
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            logger.error(f"拉取任务找不到订阅 ID={subscription_id}")
            return
        source_list = [{"url": subscription.url, "enabled": True, "name": subscription.name}]
        logger.info(f"开始解析订阅源: {subscription.url}")

        hosts = await parse_all_sources(source_list)
        logger.info(f"解析完成，共发现 {len(hosts)} 个唯一 URL")

        resolver = get_resolver()
        hosts_to_add = []
        for i, url in enumerate(hosts):
            match = re.match(r"https?://(?P<HOST>[^/]+)(?P<PATH>/.*?)(?<!\d)(?P<CODE>\d{9})(?=[#$]|$)", url)
            if not match:
                logger.warning(f"无法解析 URL: {url}")
                continue

            host_full = match.group("HOST")
            path = match.group("PATH")
            code = match.group("CODE")
            if ":" in host_full:
                host, port_str = host_full.rsplit(":", 1)
                port = int(port_str)
            else:
                host = host_full
                port = 80

            logger.debug(f"验证 HOST [{i+1}/{len(hosts)}]: {host}:{port} {path}{code}")

            existing = db.query(Host).filter(Host.host == f"{host}:{port}").first()
            if existing:
                logger.debug(f"HOST 已存在，跳过: {host}:{port}")
                skipped += 1
                continue

            try:
                info = await resolver.resolve_host(host, port, path)
                if not info.get("valid", False):
                    logger.warning(f"HOST 验证失败，跳过: {host}:{port}, error={info.get('error', 'unknown')}")
                    skipped += 1
                    continue
                now = timestamp_shanghai()
                full_url = f"http://{host}:{port}{path}"
                new_host = Host(
                    host=info["host"], full_path=full_url, province=info["province"],
                    isp=info["isp"], latency=info.get("latency"),
                    created_at=now, updated_at=now
                )
                hosts_to_add.append(new_host)
                added += 1
                logger.info(f"验证通过: {host}:{port}, 省份={info['province']}, ISP={info['isp']}")
            except Exception as e:
                errors.append(f"{host}:{port}: {str(e)}")
                logger.error(f"验证失败: {host}:{port} - {e}", exc_info=True)

        subscription.updated_at = timestamp_shanghai()
        # 批量写入，使用写锁保护整个事务
        duplicate_count = 0
        with db_write_lock:
            for h in hosts_to_add:
                db.add(h)
            try:
                db.commit()
            except exc.IntegrityError:
                db.rollback()
                duplicate_count = len(hosts_to_add)
                logger.warning(f"插入 host 时遇到重复数据，跳过 {duplicate_count} 条")
        logger.info(f"拉取完成: 新增 {added} 个 HOST, 跳过 {skipped + duplicate_count} 个, 错误 {len(errors)} 个")

        if added > 0 or skipped > 0:
            with db_write_lock:
                create_notification(db, MSG_TYPE_SUCCESS,
                    f"订阅拉取完成: {subscription.name or subscription.url}",
                    f"新增 {added} 个主机，跳过 {skipped} 个",
                    "订阅管理"
                )
    except Exception as e:
        logger.error(f"拉取过程发生严重错误: {e}", exc_info=True)
        try:
            with db_write_lock:
                create_notification(db, MSG_TYPE_ERROR,
                    f"订阅拉取失败: {subscription.name or subscription.url}",
                    str(e),
                    "订阅管理"
                )
        except Exception as notif_e:
            logger.error(f"发送通知失败: {notif_e}")
    finally:
        db.close()


@app.post("/subscriptions/{subscription_id}/fetch")
async def fetch_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise BusinessException("订阅不存在", ErrorCode.NOT_FOUND)

    asyncio.create_task(_pull_subscription(subscription_id))
    return success_response(msg="拉取任务已启动")


@app.post("/subscriptions/fetch-all")
async def fetch_all_subscriptions(db: Session = Depends(get_db)):
    sources = db.query(Subscription).filter(Subscription.enabled == True).all()
    if not sources:
        logger.warning("没有启用的订阅")
        return success_response(data=None, msg="没有启用的订阅")

    for subscription in sources:
        asyncio.create_task(_pull_subscription(subscription.id))

    return success_response(msg=f"已启动 {len(sources)} 个拉取任务")


# ============ 频道管理 API ============

@app.get("/channels")
async def get_channels(db: Session = Depends(get_db)):
    """获取频道列表（按分组展示）"""
    # 获取所有可见分组
    groups = db.query(ChannelGroup).filter(ChannelGroup.visible == True).order_by(ChannelGroup.sort_order.asc()).all()
    visible_group_ids = {g.id for g in groups}
    groups_dict = {g.id: {"id": g.id, "name": g.name, "channels": []} for g in groups}

    # 获取所有频道，只保留未分组或可见分组的频道
    channels = db.query(Channel).filter(
        (Channel.group_id == 0) | (Channel.group_id.in_(visible_group_ids))
    ).order_by(Channel.created_at.asc()).all()
    for ch in channels:
        if ch.group_id in groups_dict:
            groups_dict[ch.group_id]["channels"].append({
                "id": ch.id,
                "name": ch.name,
                "code": ch.code,
                "logoName": ch.logo_name or "",
                "groupId": ch.group_id,
                "groupName": groups_dict[ch.group_id]["name"],
                "createdAt": ch.created_at,
            })

    # 转换为列表格式
    result = []
    for g in groups:
        group_data = groups_dict[g.id]
        result.append({
            "id": g.id,
            "name": g.name,
            "createdAt": g.created_at,
            "channels": group_data["channels"],
        })

    # 添加未分组的频道
    ungrouped_channels = [ch for ch in channels if ch.group_id not in groups_dict]
    if ungrouped_channels:
        result.append({
            "id": 0,
            "name": "未分组",
            "createdAt": 0,
            "channels": [{
                "id": ch.id,
                "name": ch.name,
                "code": ch.code,
                "logoName": ch.logo_name or "",
                "groupId": ch.group_id,
                "groupName": "未分组",
                "createdAt": ch.created_at,
            } for ch in ungrouped_channels],
        })

    return success_response(data=result)


@app.get("/channel-groups")
async def get_channel_groups(db: Session = Depends(get_db)):
    """获取分组列表"""
    groups = db.query(ChannelGroup).order_by(ChannelGroup.sort_order.asc()).all()
    return success_response(data=[{
        "id": g.id,
        "name": g.name,
        "createdAt": g.created_at,
        "visible": g.visible,
    } for g in groups])


class ChannelGroupCreate(BaseModel):
    name: str


class ChannelGroupUpdate(BaseModel):
    name: str


@app.post("/channel-groups")
async def create_channel_group(body: ChannelGroupCreate, db: Session = Depends(get_db)):
    """创建分组"""
    name = body.name.strip()
    if not name:
        raise BusinessException("分组名称不能为空", ErrorCode.PARAM_ERROR)
    if len(name) > 10:
        raise BusinessException("分组名称最多10个字符", ErrorCode.PARAM_ERROR)
    existing = db.query(ChannelGroup).filter(ChannelGroup.name == name).first()
    if existing:
        raise BusinessException("分组名称已存在", ErrorCode.DUPLICATE)
    now = timestamp_shanghai()
    # 使用最大 sort_order + 1，确保唯一性
    max_sort = db.query(func.max(ChannelGroup.sort_order)).scalar() or 0
    group = ChannelGroup(name=name, created_at=now, sort_order=max_sort + 1, visible=True)
    db.add(group)
    with db_write_lock:
        db.commit()
    db.refresh(group)
    return success_response(data={"id": group.id, "name": group.name}, msg="创建成功")


@app.put("/channel-groups/{group_id}")
async def update_channel_group(group_id: int, body: ChannelGroupUpdate, db: Session = Depends(get_db)):
    """更新分组名称"""
    group = db.query(ChannelGroup).filter(ChannelGroup.id == group_id).first()
    if not group:
        raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
    name = body.name.strip()
    if not name:
        raise BusinessException("分组名称不能为空", ErrorCode.PARAM_ERROR)
    if len(name) > 10:
        raise BusinessException("分组名称最多10个字符", ErrorCode.PARAM_ERROR)
    existing = db.query(ChannelGroup).filter(ChannelGroup.name == name, ChannelGroup.id != group_id).first()
    if existing:
        raise BusinessException("分组名称已存在", ErrorCode.DUPLICATE)
    group.name = name
    with db_write_lock:
        db.commit()
    return success_response(msg="更新成功")


@app.delete("/channel-groups/{group_id}")
async def delete_channel_group(group_id: int, db: Session = Depends(get_db)):
    """删除分组（将频道移入未分组）"""
    group = db.query(ChannelGroup).filter(ChannelGroup.id == group_id).first()
    if not group:
        raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
    # 将该分组下的所有频道移入"未分组"(group_id=0)
    with db_write_lock:
        db.query(Channel).filter(Channel.group_id == group_id).update({"group_id": 0})
        db.delete(group)
        db.commit()
    return success_response(msg="删除成功")


@app.post("/channel-groups/{group_id}/move-up")
async def move_group_up(group_id: int, db: Session = Depends(get_db)):
    """将分组上移"""
    group = db.query(ChannelGroup).filter(ChannelGroup.id == group_id).first()
    if not group:
        raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
    groups = db.query(ChannelGroup).order_by(ChannelGroup.sort_order.asc()).all()
    idx = next((i for i, g in enumerate(groups) if g.id == group_id), None)
    if idx is None or idx == 0:
        return success_response()
    prev_group = groups[idx - 1]
    prev_group.sort_order, group.sort_order = group.sort_order, prev_group.sort_order
    with db_write_lock:
        db.commit()
    return success_response(msg="上移成功")


@app.post("/channel-groups/{group_id}/move-down")
async def move_group_down(group_id: int, db: Session = Depends(get_db)):
    """将分组下移"""
    group = db.query(ChannelGroup).filter(ChannelGroup.id == group_id).first()
    if not group:
        raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
    groups = db.query(ChannelGroup).order_by(ChannelGroup.sort_order.asc()).all()
    idx = next((i for i, g in enumerate(groups) if g.id == group_id), None)
    if idx is None or idx == len(groups) - 1:
        return success_response()
    next_group = groups[idx + 1]
    next_group.sort_order, group.sort_order = group.sort_order, next_group.sort_order
    with db_write_lock:
        db.commit()
    return success_response(msg="下移成功")


@app.post("/channel-groups/{group_id}/toggle-visible")
async def toggle_group_visible(group_id: int, db: Session = Depends(get_db)):
    """切换分组显示/隐藏"""
    group = db.query(ChannelGroup).filter(ChannelGroup.id == group_id).first()
    if not group:
        raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
    group.visible = not group.visible
    with db_write_lock:
        db.commit()
    return success_response(data={"visible": group.visible}, msg="已更新")


class ChannelImportItem(BaseModel):
    name: str
    code: str  # 9位数字CODE
    group: str  # 分组名称
    logo_name: str = ""  # 台标文件名


class ChannelBatchImport(BaseModel):
    channels: list[ChannelImportItem]


@app.post("/channels/batch-import")
async def batch_import_channels(body: ChannelBatchImport, db: Session = Depends(get_db)):
    """批量导入频道（按CODE去重）"""
    added_channels = 0
    skipped_codes = []
    created_groups = []

    now = timestamp_shanghai()

    # 获取已存在的CODE集合
    existing_codes = set(db.query(Channel.code).all())
    existing_codes = {c[0] for c in existing_codes}

    # 处理每个频道
    for item in body.channels:
        code = item.code.strip()
        if not code:
            continue

        # 检查CODE是否已存在
        if code in existing_codes:
            skipped_codes.append(code)
            continue

        # 处理分组（跳过已存在的）
        group_name = (item.group or "未分组").strip()
        existing_group = db.query(ChannelGroup).filter(ChannelGroup.name == group_name).first()
        if existing_group:
            group_id = existing_group.id
        else:
            # 计算新的 sort_order
            max_sort = db.query(func.max(ChannelGroup.sort_order)).scalar() or 0
            new_group = ChannelGroup(name=group_name, created_at=now, sort_order=max_sort + 1, visible=True)
            db.add(new_group)
            db.flush()
            group_id = new_group.id
            created_groups.append(group_name)

        # 创建频道
        new_channel = Channel(
            name=item.name.strip(),
            code=code,
            logo_name=item.name.strip(),  # 默认使用名称作为台标名
            group_id=group_id,
            created_at=now,
        )
        db.add(new_channel)
        existing_codes.add(code)
        added_channels += 1

    with db_write_lock:
        db.commit()

    msg = f"导入成功 {added_channels} 个频道"
    if skipped_codes:
        msg += f"，跳过 {len(skipped_codes)} 个重复CODE"
    if created_groups:
        msg += f"，创建 {len(created_groups)} 个新分组"

    logger.info(f"批量导入完成: 新增{added_channels}，跳过{len(skipped_codes)}，新建分组{len(created_groups)}")
    return success_response(data={"added": added_channels, "skipped": len(skipped_codes), "newGroups": len(created_groups)}, msg=msg)


class ChannelBatchImportURL(BaseModel):
    url: str


@app.post("/channels/batch-import-preview")
async def batch_import_preview(body: ChannelBatchImportURL, db: Session = Depends(get_db)):
    """预览远程URL中的频道数据（不导入，仅返回解析结果）"""
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL不能为空")

    # 确保 URL 有协议前缀
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url

    try:
        resp = requests.get(url, timeout=30, headers={'User-Agent': 'MiguManager/1.0'})
        resp.raise_for_status()
        content = resp.text
    except requests.exceptions.RequestException as e:
        logger.error(f"获取URL内容失败: {e}")
        raise HTTPException(status_code=400, detail=f"获取URL内容失败: {e}")

    # 解析内容
    raw_channels = detect_and_parse(content, url)
    channels = filter_migu_channels(raw_channels)

    if not channels:
        raise HTTPException(status_code=400, detail="未能从URL中解析到任何Migu频道数据")

    # 去重
    seen_codes = set()
    dedup_channels = []
    for ch in channels:
        code = extract_code(ch['url'])
        if code and code in seen_codes:
            continue
        if code:
            seen_codes.add(code)
        dedup_channels.append(ch)

    # 构建分组结构
    groups = {}
    for ch in dedup_channels:
        group_name = ch.get('group') or '未分组'
        if group_name not in groups:
            groups[group_name] = {'name': group_name, 'channels': []}
        groups[group_name]['channels'].append(ch)

    result = {
        'channels': dedup_channels,
        'totalRaw': len(channels),
        'totalDedup': len(dedup_channels),
        'groups': list(groups.values())
    }

    logger.info(f"URL预览完成: {url} -> 原始{len(channels)}个，去重后{len(dedup_channels)}个")
    return success_response(data=result, msg=f"成功解析 {len(dedup_channels)} 个频道")


class BatchDeleteChannels(BaseModel):
    channel_ids: list[int]


@app.post("/channels/batch-delete")
async def batch_delete_channels(body: BatchDeleteChannels, db: Session = Depends(get_db)):
    """批量删除频道"""
    if not body.channel_ids:
        raise BusinessException("请选择要删除的频道", ErrorCode.PARAM_ERROR)

    count = db.query(Channel).filter(Channel.id.in_(body.channel_ids)).delete()
    with db_write_lock:
        db.commit()
    logger.info(f"批量删除频道完成: 删除{count}个")
    return success_response(data={"deleted": count}, msg=f"已删除 {count} 个频道")


class BatchGroupUpdate(BaseModel):
    channel_ids: list[int]
    group_id: int


@app.post("/channels/batch-update-group")
async def batch_update_channel_group(body: BatchGroupUpdate, db: Session = Depends(get_db)):
    """批量更新频道分组"""
    if not body.channel_ids:
        raise BusinessException("请选择要分组的频道", ErrorCode.PARAM_ERROR)

    group_name = "未分组"
    if body.group_id != 0:
        group = db.query(ChannelGroup).filter(ChannelGroup.id == body.group_id).first()
        if not group:
            raise BusinessException("分组不存在", ErrorCode.NOT_FOUND)
        group_name = group.name

    db.query(Channel).filter(Channel.id.in_(body.channel_ids)).update({"group_id": body.group_id})
    with db_write_lock:
        db.commit()
    return success_response(data={"updated": len(body.channel_ids)}, msg=f"已将 {len(body.channel_ids)} 个频道移动到「{group_name}」")


@app.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int, db: Session = Depends(get_db)):
    """删除频道"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise BusinessException("频道不存在", ErrorCode.NOT_FOUND)
    with db_write_lock:
        db.delete(channel)
        db.commit()
    return success_response(msg="删除成功")


class ChannelCreate(BaseModel):
    name: str
    code: str
    logo_name: str = ""
    group_id: Optional[int] = None


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    logo_name: Optional[str] = None
    group_id: Optional[int] = None


@app.post("/channels")
async def create_channel(body: ChannelCreate, db: Session = Depends(get_db)):
    """创建单个频道"""
    code = body.code.strip()
    if not code:
        raise BusinessException("CODE不能为空", ErrorCode.PARAM_ERROR)

    # 检查 CODE 是否已存在
    existing = db.query(Channel).filter(Channel.code == code).first()
    if existing:
        raise BusinessException("CODE已存在", ErrorCode.DUPLICATE)

    now = timestamp_shanghai()
    new_channel = Channel(
        name=body.name.strip(),
        code=code,
        logo_name=body.logo_name.strip() if body.logo_name else body.name.strip(),
        group_id=body.group_id if body.group_id is not None else 0,
        created_at=now,
    )
    db.add(new_channel)
    with db_write_lock:
        db.commit()
    db.refresh(new_channel)
    return success_response(data={
        "id": new_channel.id,
        "name": new_channel.name,
        "code": new_channel.code,
        "logoName": new_channel.logo_name or "",
        "groupId": new_channel.group_id,
        "createdAt": new_channel.created_at,
    }, msg="创建成功")


@app.put("/channels/{channel_id}")
async def update_channel(channel_id: int, body: ChannelUpdate, db: Session = Depends(get_db)):
    """更新单个频道"""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise BusinessException("频道不存在", ErrorCode.NOT_FOUND)

    if body.code is not None:
        code = body.code.strip()
        if not code:
            raise BusinessException("CODE不能为空", ErrorCode.PARAM_ERROR)
        # 检查 CODE 是否被其他频道使用
        existing = db.query(Channel).filter(Channel.code == code, Channel.id != channel_id).first()
        if existing:
            raise BusinessException("CODE已被其他频道使用", ErrorCode.DUPLICATE)
        channel.code = code

    if body.name is not None:
        channel.name = body.name.strip()

    if body.logo_name is not None:
        channel.logo_name = body.logo_name.strip()

    if body.group_id is not None:
        channel.group_id = body.group_id

    with db_write_lock:
        db.commit()
    db.refresh(channel)
    return success_response(data={
        "id": channel.id,
        "name": channel.name,
        "code": channel.code,
        "logoName": channel.logo_name or "",
        "groupId": channel.group_id,
        "createdAt": channel.created_at,
    }, msg="更新成功")


# ============ 播放代理接口 ============

@app.get("/live/{channel_code}")
async def proxy_channel(
    channel_code: str,
    db: Session = Depends(get_db),
):
    """播放代理接口：返回频道直播URL（302重定向）"""
    if not channel_code or not re.match(r"^\d{9}$", channel_code):
        raise BusinessException("CODE 必须为9位数字", ErrorCode.PARAM_ERROR)

    try:
        play_url = playback_service.resolve_play_url(db, channel_code)
    except BusinessException:
        raise
    except Exception as e:
        logger.error(f"频道 {channel_code} 获取播放URL失败: {e}")
        raise BusinessException(str(e), ErrorCode.SERVER_ERROR)

    return Response(
        status_code=302,
        headers={"Location": play_url}
    )


# ============ 播放缓存查询接口 ============

@app.get("/playback-caches")
async def get_playback_caches(db: Session = Depends(get_db)):
    """查询所有已缓存的播放URL"""
    from models import ChannelPlayUrl
    caches = db.query(ChannelPlayUrl).all()
    return success_response(data=[
        {
            "id": c.id,
            "channelCode": c.channel_code,
            "playUrl": c.play_url,
            "ttl": c.ttl,
            "createdAt": c.created_at,
        }
        for c in caches
    ])


# ============ 订阅接口（txt / m3u）============

@app.get("/sub/txt")
async def sub_txt(request: Request, db: Session = Depends(get_db)):
    """返回所有频道的播放 URL 列表（带分组和名称）"""
    # 读取 nginx 传入的 prefix，本地开发时为空
    prefix = request.headers.get("x-forwarded-prefix", "")
    host = request.headers.get("host", "localhost:2847")
    scheme = request.url.scheme
    base = f"{scheme}://{host}{prefix}/live"
    groups = db.query(ChannelGroup).filter(ChannelGroup.visible == True).order_by(ChannelGroup.sort_order.asc()).all()
    visible_group_ids = {g.id for g in groups}
    groups_dict = {g.id: {"id": g.id, "name": g.name, "channels": []} for g in groups}

    channels = db.query(Channel).filter(
        (Channel.group_id == 0) | (Channel.group_id.in_(visible_group_ids))
    ).order_by(Channel.created_at.asc()).all()
    for ch in channels:
        if ch.group_id in groups_dict:
            groups_dict[ch.group_id]["channels"].append(ch)

    ungrouped = [ch for ch in channels if ch.group_id not in groups_dict]

    lines = []
    for g in groups:
        lines.append(f"{g.name},#genre#")
        for ch in groups_dict[g.id]["channels"]:
            lines.append(f"{ch.name},{base}/{ch.code}")

    if ungrouped:
        lines.append("未分组,#genre#")
        for ch in ungrouped:
            lines.append(f"{ch.name},{base}/{ch.code}")

    return Response(content="\n".join(lines) + "\n", media_type="text/plain")


@app.get("/sub/m3u")
async def sub_m3u(request: Request, db: Session = Depends(get_db)):
    """返回 M3U 格式的订阅列表"""
    # 读取 nginx 传入的 prefix，本地开发时为空
    prefix = request.headers.get("x-forwarded-prefix", "")
    host = request.headers.get("host", "localhost:2847")
    scheme = request.url.scheme
    base = f"{scheme}://{host}{prefix}/live"
    groups = db.query(ChannelGroup).filter(ChannelGroup.visible == True).order_by(ChannelGroup.sort_order.asc()).all()
    visible_group_ids = {g.id for g in groups}
    groups_dict = {g.id: {"id": g.id, "name": g.name, "channels": []} for g in groups}

    channels = db.query(Channel).filter(
        (Channel.group_id == 0) | (Channel.group_id.in_(visible_group_ids))
    ).order_by(Channel.created_at.asc()).all()
    for ch in channels:
        if ch.group_id in groups_dict:
            groups_dict[ch.group_id]["channels"].append(ch)

    ungrouped = [ch for ch in channels if ch.group_id not in groups_dict]

    lines = ["#EXTM3U"]
    for g in groups:
        for ch in groups_dict[g.id]["channels"]:
            logo = f"https://v4.gh-proxy.org/https://raw.githubusercontent.com/fanmingming/live/refs/heads/main/tv/{ch.logo_name}.png" if ch.logo_name else ""
            lines.append(f'#EXTINF:-1 group-title="{g.name}" tvg-name="{ch.name}" tvg-logo="{logo}",{ch.name}')
            lines.append(f"{base}/{ch.code}")

    if ungrouped:
        for ch in ungrouped:
            logo = f"https://v4.gh-proxy.org/https://raw.githubusercontent.com/fanmingming/live/refs/heads/main/tv/{ch.logo_name}.png" if ch.logo_name else ""
            lines.append(f'#EXTINF:-1 group-title="未分组" tvg-name="{ch.name}" tvg-logo="{logo}",{ch.name}')
            lines.append(f"{base}/{ch.code}")

    return Response(content="\n".join(lines) + "\n", media_type="application/x-mpegURL")


# 注册通知路由（必须在此处，不能在 __main__ 块内）
from routers import notifications
app.include_router(notifications.router, tags=["通知中心"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2847)
