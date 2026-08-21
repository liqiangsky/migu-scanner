import asyncio
import re
import uuid
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import Subscription, Host
from services.url_parser import parse_all_sources
from services.host_resolver import get_resolver, TEST_CHANNEL_CODE
from config import settings, timestamp_shanghai

# 配置控制台日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("migu")

# 异步拉取进度追踪
_progress_tracker: dict = {}
_progress_lock = asyncio.Lock()


async def emit_progress(task_id: str, event: str, data: dict):
    async with _progress_lock:
        if task_id in _progress_tracker:
            _progress_tracker[task_id]["events"].append({
                "event": event,
                "data": data,
                "ts": timestamp_shanghai()
            })
            if len(_progress_tracker[task_id]["events"]) > 50:
                _progress_tracker[task_id]["events"] = _progress_tracker[task_id]["events"][-50:]


def create_task_progress(task_id: str, label: str = ""):
    _progress_tracker[task_id] = {
        "task_id": task_id,
        "label": label,
        "status": "running",
        "started_at": timestamp_shanghai(),
        "completed_at": None,
        "added": 0,
        "skipped": 0,
        "total_parsed": 0,
        "events": [],
        "error": None
    }
    logger.info(f"[Task {task_id}] 创建任务: {label}")


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


def success_response(data=None, msg="success"):
    return {"code": 200, "data": data, "msg": msg}


# ============ 订阅管理 API ============

@app.get("/api/subscriptions")
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


@app.post("/api/subscriptions")
async def add_subscription(body: SubscriptionCreate, db: Session = Depends(get_db)):
    url = body.url.strip()
    logger.info(f"添加订阅请求: name='{body.name}', url='{url}'")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    existing = db.query(Subscription).filter(Subscription.url == url).first()
    if existing:
        logger.warning(f"添加订阅失败: URL 已存在 {url}")
        raise HTTPException(status_code=400, detail="URL already exists")
    now = timestamp_shanghai()
    source = Subscription(
        name=body.name.strip(), url=url, enabled=True,
        fetch_cron=body.fetch_cron.strip(), created_at=now, updated_at=now
    )
    db.add(source)
    db.commit()
    logger.info(f"添加订阅成功: ID={source.id}, name='{body.name}', url='{url}'")
    return success_response(data={"id": source.id}, msg="添加成功")


@app.put("/api/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: int, body: SubscriptionUpdate, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    logger.info(f"更新订阅: ID={subscription_id}")
    if body.name is not None:
        subscription.name = body.name.strip()
    if body.url is not None:
        url = body.url.strip()
        dup = db.query(Subscription).filter(Subscription.url == url, Subscription.id != subscription_id).first()
        if dup:
            raise HTTPException(status_code=400, detail="URL already exists")
        subscription.url = url
    if body.enabled is not None:
        subscription.enabled = body.enabled
    if body.fetch_cron is not None:
        subscription.fetch_cron = body.fetch_cron.strip()
    subscription.updated_at = timestamp_shanghai()
    db.commit()
    logger.info(f"更新订阅成功: ID={subscription_id}")
    return success_response(msg="更新成功")


@app.delete("/api/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    logger.info(f"删除订阅: ID={subscription_id}, url={subscription.url}")
    db.delete(subscription)
    db.commit()
    logger.info(f"删除订阅成功: ID={subscription_id}")
    return success_response(msg="删除成功")


# ============ HOST 管理 API ============

@app.get("/api/hosts")
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


@app.get("/api/hosts/filters")
async def get_host_filters(db: Session = Depends(get_db)):
    """获取筛选选项（地区和运营商的去重列表）"""
    from sqlalchemy import distinct
    province_list = db.query(distinct(Host.province)).filter(Host.province != "").all()
    isp_list = db.query(distinct(Host.isp)).filter(Host.isp != "").all()
    provinces = [row[0] for row in province_list if row[0]]
    isps = [row[0] for row in isp_list if row[0]]
    return success_response(data={"provinces": provinces, "isps": isps})


@app.delete("/api/hosts/{host_id}")
async def delete_host(host_id: int, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    logger.info(f"删除主机: ID={host_id}, host={host.host}")
    db.delete(host)
    db.commit()
    logger.info(f"删除主机成功: ID={host_id}")
    return success_response(msg="删除成功")


@app.post("/api/hosts/{host_id}/test-delay")
async def test_host_delay(host_id: int, db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")

    resolver = get_resolver()
    # 直接从 full_path 拼接 TEST_CHANNEL_CODE
    test_url = f"{host.full_path.rstrip('/')}/{TEST_CHANNEL_CODE}"
    result = await resolver.test_host(test_url)
    latency = result.get("latency", -1)

    host.latency = latency
    host.updated_at = timestamp_shanghai()
    db.commit()

    return success_response(data={
        "delay": latency,
        "updatedAt": host.updated_at
    }, msg="success")


# ============ 拉取 API ============

@app.post("/api/subscriptions/{subscription_id}/fetch")
async def fetch_subscription(subscription_id: int, db: Session = Depends(get_db)):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    task_id = str(uuid.uuid4())
    label = f"拉取订阅: {subscription.name or subscription.url}"
    logger.info(f"[Task {task_id}] 启动单订阅拉取: {label}")
    create_task_progress(task_id, label)

    async def _pull_with_progress():
        added = 0
        skipped = 0
        errors = []
        try:
            source_list = [{"url": subscription.url, "enabled": True, "name": subscription.name}]
            logger.info(f"[Task {task_id}] 开始解析订阅源: {subscription.url}")

            async def on_progress(event: str, data: dict):
                await emit_progress(task_id, event, data)

            hosts = await parse_all_sources(source_list, on_progress=on_progress)
            logger.info(f"[Task {task_id}] 解析完成，共发现 {len(hosts)} 个唯一 URL")
            await emit_progress(task_id, "resolving", {"total": len(hosts)})

            resolver = get_resolver()
            for i, url in enumerate(hosts):
                # 分解 URL 为 host, port, path, code
                # 格式: http://host:port/path/999999999
                match = re.match(r"https?://(?P<HOST>[^/]+)(?P<PATH>/.*?)(?<!\d)(?P<CODE>\d{9})(?=[#$]|$)", url)
                if not match:
                    logger.warning(f"[Task {task_id}] 无法解析 URL: {url}")
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


                logger.debug(f"[Task {task_id}] 验证 HOST [{i+1}/{len(hosts)}]: {host}:{port} {path}{code}")
                await emit_progress(task_id, "resolving_host", {
                    "index": i + 1, "total": len(hosts), "host": f"{host}:{port}"
                })

                existing = db.query(Host).filter(Host.host == f"{host}:{port}").first()
                if existing:
                    logger.debug(f"[Task {task_id}] HOST 已存在，跳过: {host}:{port}")
                    skipped += 1
                    continue

                try:
                    info = await resolver.resolve_host(host, port, path)
                    if not info.get("valid", False):
                        logger.warning(f"[Task {task_id}] HOST 验证失败，跳过: {host}:{port}, error={info.get('error', 'unknown')}")
                        skipped += 1
                        continue
                    now = timestamp_shanghai()
                    # 构造完整URL（不含CODE）
                    full_url = f"http://{host}:{port}{path}"
                    new_host = Host(
                        host=info["host"], full_path=full_url, province=info["province"],
                        isp=info["isp"], latency=info.get("latency"),
                        created_at=now, updated_at=now
                    )
                    db.add(new_host)
                    added += 1
                    logger.info(f"[Task {task_id}] 验证通过: {host}:{port}, 省份={info['province']}, ISP={info['isp']}")
                except Exception as e:
                    errors.append(f"{host}:{port}: {str(e)}")
                    logger.error(f"[Task {task_id}] 验证失败: {host}:{port} - {e}", exc_info=True)

            subscription.updated_at = timestamp_shanghai()
            db.commit()
            logger.info(f"[Task {task_id}] 拉取完成: 新增 {added} 个 HOST, 跳过 {skipped} 个, 错误 {len(errors)} 个")

            await emit_progress(task_id, "completed", {
                "added": added, "skipped": skipped,
                "total_parsed": len(hosts), "errors": errors[:5]
            })
        except Exception as e:
            logger.error(f"[Task {task_id}] 拉取过程发生严重错误: {e}", exc_info=True)
            await emit_progress(task_id, "error", {"message": str(e)})
        finally:
            async with _progress_lock:
                if task_id in _progress_tracker:
                    _progress_tracker[task_id]["status"] = "done"
                    _progress_tracker[task_id]["completed_at"] = timestamp_shanghai()

    asyncio.create_task(_pull_with_progress())
    return success_response(data={"task_id": task_id, "label": label}, msg="拉取任务已启动")


@app.post("/api/subscriptions/fetch-all")
async def fetch_all_subscriptions(db: Session = Depends(get_db)):
    sources = db.query(Subscription).filter(Subscription.enabled == True).all()
    if not sources:
        logger.warning("没有启用的订阅")
        return success_response(data=None, msg="没有启用的订阅")

    task_id = str(uuid.uuid4())
    label = f"批量拉取 {len(sources)} 个订阅"
    logger.info(f"[Task {task_id}] 启动批量拉取: {label}")
    create_task_progress(task_id, label)

    source_list = [{"url": s.url, "enabled": True, "name": s.name} for s in sources]

    async def _pull_all_with_progress():
        added = 0
        skipped = 0
        errors = []
        try:
            async def on_progress(event: str, data: dict):
                await emit_progress(task_id, event, data)

            logger.info(f"[Task {task_id}] 开始解析 {len(source_list)} 个订阅源")
            hosts = await parse_all_sources(source_list, on_progress=on_progress)
            logger.info(f"[Task {task_id}] 解析完成，共发现 {len(hosts)} 个唯一 URL")
            await emit_progress(task_id, "resolving", {"total": len(hosts)})

            resolver = get_resolver()
            for i, url in enumerate(hosts):
                # 分解 URL 为 host, port, path, code
                match = re.match(r'https?://(?P<HOST>[^/]+)(?P<PATH>/.*?)(?<!\d)(?P<CODE>\d{9})(?=[#$]|$)', url)
                if not match:
                    logger.warning(f"[Task {task_id}] 无法解析 URL: {url}")
                    continue

                host_full = match.group('HOST')
                path = match.group('PATH')
                # 分解 host_full 为 ip 和 port
                if ':' in host_full:
                    host, port_str = host_full.rsplit(':', 1)
                    port = int(port_str)
                else:
                    host = host_full
                    port = 80

                logger.debug(f"[Task {task_id}] 验证 HOST [{i+1}/{len(hosts)}]: {host}:{port}")
                await emit_progress(task_id, "resolving_host", {
                    "index": i + 1, "total": len(hosts), "host": f"{host}:{port}"
                })

                existing = db.query(Host).filter(Host.host == f"{host}:{port}").first()
                if existing:
                    logger.debug(f"[Task {task_id}] HOST 已存在，跳过: {host}:{port}")
                    skipped += 1
                    continue

                try:
                    info = await resolver.resolve_host(host, port, path)
                    if not info.get("valid", False):
                        logger.warning(f"[Task {task_id}] HOST 验证失败，跳过: {host}:{port}, error={info.get('error', 'unknown')}")
                        skipped += 1
                        continue
                    now = timestamp_shanghai()
                    # 构造完整URL（不含CODE）
                    full_url = f"http://{host}:{port}{path}"
                    new_host = Host(
                        host=info["host"], full_path=full_url, province=info["province"],
                        isp=info["isp"], latency=info.get("latency"),
                        created_at=now, updated_at=now
                    )
                    db.add(new_host)
                    added += 1
                    logger.info(f"[Task {task_id}] 验证通过: {host}:{port}")
                except Exception as e:
                    errors.append(f"{host}:{port}: {str(e)}")
                    logger.error(f"[Task {task_id}] 验证失败: {host}:{port} - {e}", exc_info=True)

            now = timestamp_shanghai()
            for s in sources:
                s.updated_at = now
            db.commit()
            logger.info(f"[Task {task_id}] 批量拉取完成: 新增 {added} 个 HOST, 跳过 {skipped} 个, 错误 {len(errors)} 个")

            await emit_progress(task_id, "completed", {
                "added": added, "skipped": skipped,
                "total_parsed": len(hosts), "errors": errors[:5]
            })
        except Exception as e:
            logger.error(f"[Task {task_id}] 批量拉取过程发生严重错误: {e}", exc_info=True)
            await emit_progress(task_id, "error", {"message": str(e)})
        finally:
            async with _progress_lock:
                if task_id in _progress_tracker:
                    _progress_tracker[task_id]["status"] = "done"
                    _progress_tracker[task_id]["completed_at"] = timestamp_shanghai()

    asyncio.create_task(_pull_all_with_progress())
    return success_response(data={"task_id": task_id, "label": label}, msg="批量拉取任务已启动")


# ============ 任务进度 API ============

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    async with _progress_lock:
        task = _progress_tracker.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return success_response(data={
        "task_id": task["task_id"], "label": task["label"],
        "status": task["status"],
        "added": task.get("added", 0), "skipped": task.get("skipped", 0),
        "total_parsed": task.get("total_parsed", 0),
        "started_at": task["started_at"], "completed_at": task["completed_at"],
        "error": task.get("error"), "events": task.get("events", [])[-20:]
    })


@app.get("/api/tasks")
async def list_tasks():
    async with _progress_lock:
        tasks = list(_progress_tracker.values())
    return success_response(data=tasks)


@app.delete("/api/tasks/{task_id}")
async def clear_task(task_id: str):
    async with _progress_lock:
        if task_id in _progress_tracker:
            del _progress_tracker[task_id]
            logger.info(f"清除任务记录: {task_id}")
            return success_response(msg="已清除")
    raise HTTPException(status_code=404, detail="Task not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2847)
