import asyncio
import aiohttp
import time
import os
import threading
import ipaddress
import logging
from typing import Optional, Tuple
from config import settings

import ip2region.searcher as xdb_searcher
import ip2region.util as xdb_util

logger = logging.getLogger("migu.resolver")

TEST_CHANNEL_CODE = "608807420"


class HostResolver:
    def __init__(self):
        self.searcher = None
        self._lock = threading.Lock()
        self._load_ip2region()

    def _load_ip2region(self):
        db_path = settings.ip2region_db
        if not os.path.exists(db_path):
            logger.error(f"IP2Region database not found at {db_path}")
            return
        try:
            c_buffer = xdb_util.load_content_from_file(db_path)
            self.searcher = xdb_searcher.new_with_buffer(xdb_util.IPv4, c_buffer)
            logger.info(f"Loaded ip2region from {db_path}")
        except Exception as e:
            logger.error(f"Failed to load ip2region: {e}", exc_info=True)

    def _is_ip_addr(self, s: str) -> bool:
        try:
            ipaddress.ip_address(s)
            return True
        except ValueError:
            return False

    async def _resolve_to_ip(self, host: str) -> str:
        ip_part = host.rsplit(":", 1)[0] if ":" in host else host
        if self._is_ip_addr(ip_part):
            return ip_part
        try:
            loop = asyncio.get_running_loop()
            addrs = await loop.getaddrinfo(ip_part, None, family=2)
            for addr in addrs:
                ip = addr[4][0]
                logger.debug(f"DNS resolved {ip_part} -> {ip}")
                return ip
        except Exception as e:
            logger.error(f"DNS resolution failed for {ip_part}: {e}")
        return ""

    def _clean_province(self, province: str) -> str:
        """Remove administrative suffixes like 省, 市, 自治区, 特别行政区."""
        for suffix in ("维吾尔自治区", "壮族自治区", "自治区", "特别行政区", "省", "市"):
            if province.endswith(suffix):
                province = province[:-len(suffix)]
                break
        return province

    def get_location(self, ip: str) -> dict:
        if self.searcher is None:
            logger.warning("IP2Region searcher not initialized")
            return {"province": "Unknown", "isp": "Unknown"}
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return {"province": "", "isp": ""}
        except ValueError:
            pass
        try:
            region_str = self.searcher.search(ip)
            if not region_str:
                logger.warning(f"No location found for IP: {ip}")
                return {"province": "", "isp": "Unknown"}
            parts = region_str.split("|")
            if len(parts) >= 5:
                province = self._clean_province(parts[1]) if parts[1] else ""
                isp = parts[3] if parts[3] and parts[3] != "0" else "Unknown"
                logger.debug(f"IP {ip} location: province={province}, isp={isp}")
                return {"province": province, "isp": isp}
            return {"province": "", "isp": "Unknown"}
        except Exception as e:
            logger.error(f"IP2Region query error for {ip}: {e}", exc_info=True)
            return {"province": "", "isp": "Unknown"}

    async def test_host(self, host: str, port: int, path: str = "/") -> dict:
        test_url = f"http://{host}:{port}{path}{TEST_CHANNEL_CODE}"

        logger.debug(f"Testing host: {test_url}")

        # 浏览器 UA，避免被服务器拒绝
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 视频格式后缀（直播）
        video_extensions = ('.m3u8', '.flv', '.ts', '.mkv')

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                start = time.time()
                current_url = test_url
                max_redirects = 10

                # 手动跟踪重定向，直到找到视频URL或得到非重定向响应
                for i in range(max_redirects):
                    async with session.get(current_url, timeout=aiohttp.ClientTimeout(total=settings.latency_timeout), allow_redirects=False) as resp:
                        latency = round((time.time() - start) * 1000)

                        # 检查是否是重定向
                        if resp.status in (301, 302, 303, 307, 308):
                            location = resp.headers.get('Location', '')
                            if not location:
                                logger.warning(f"Host {host}:{port} redirect without Location at step {i+1}")
                                return {"valid": False, "error": "Redirect without Location", "latency": -1}

                            # 检查是否是视频URL（满足任一条件即可）
                            loc_lower = location.lower()
                            is_video_url = (
                                loc_lower.endswith(video_extensions) or
                                'm3u8' in loc_lower or
                                'flv' in loc_lower or
                                'miguvideo' in loc_lower
                            )
                            if is_video_url:
                                logger.info(f"Host {host}:{port} resolved to video URL after {i+1} redirects, latency: {latency}ms")
                                return {"valid": True, "error": "", "latency": latency}

                            # 继续跟随重定向
                            # 处理相对路径
                            if location.startswith('/'):
                                from urllib.parse import urljoin
                                location = urljoin(current_url, location)
                            current_url = location
                            logger.debug(f"Redirect {i+1}: {current_url[:80]}...")
                        else:
                            # 非重定向响应，读取内容检查
                            raw_body = await resp.read()

                            # 检查状态码
                            if resp.status != 200:
                                logger.warning(f"Host {host}:{port} returned status {resp.status}")
                                return {"valid": False, "error": f"HTTP {resp.status}", "latency": -1}

                            # 尝试多种编码解码
                            body = None
                            content_type = resp.headers.get('Content-Type', '').lower()
                            for encoding in ['utf-8', 'gbk', 'gb18030', 'latin1']:
                                try:
                                    body = raw_body.decode(encoding)
                                    break
                                except (UnicodeDecodeError, LookupError):
                                    continue
                            if body is None:
                                body = raw_body.decode('utf-8', errors='replace')

                            # JSON 响应直接无效
                            if 'json' in content_type or (body.strip().startswith('{') and body.strip().endswith('}')):
                                logger.warning(f"Host {host}:{port} returned JSON, invalid")
                                return {"valid": False, "error": "JSON response", "latency": -1}

                            # TXT 内容：检查是否包含 miguvideo URL
                            if 'miguvideo' in body.lower():
                                logger.info(f"Host {host}:{port} validation passed (miguvideo found), latency: {latency}ms")
                                return {"valid": True, "error": "", "latency": latency}
                            else:
                                logger.warning(f"Host {host}:{port} returned txt but no miguvideo URL: {body[:100]}")
                                return {"valid": False, "error": "No miguvideo in response", "latency": -1}

                # 超过最大重定向次数
                logger.warning(f"Host {host}:{port} too many redirects ({max_redirects})")
                return {"valid": False, "error": "Too many redirects", "latency": -1}

        except asyncio.TimeoutError:
            logger.warning(f"Host {host}:{port} channel request timeout")
            return {"valid": False, "error": "Channel timeout", "latency": -1}
        except aiohttp.ClientResponseError as e:
            logger.warning(f"Host {host}:{port} non-standard response: {e}")
            return {"valid": False, "error": str(e), "latency": -1}
        except Exception as e:
            logger.error(f"Host {host}:{port} channel request error: {e}")
            return {"valid": False, "error": str(e), "latency": -1}

    async def resolve_host(self, host: str, port: int, path: str = "/") -> dict:
        test_result = await self.test_host(host, port, path)

        ip = await self._resolve_to_ip(host)
        if ip:
            location = self.get_location(ip)
        else:
            logger.warning(f"Cannot resolve IP for host: {host}")
            location = {"province": "", "isp": "Unknown"}

        result = {
            "host": f"{host}:{port}",
            "province": location["province"],
            "isp": location["isp"],
            "latency": test_result.get("latency"),
            "valid": test_result.get("valid", False)
        }
        logger.debug(f"Host {host}:{port} resolved: province={location['province']}, isp={location['isp']}, valid={test_result.get('valid')}")
        return result


_resolver = None

def get_resolver() -> HostResolver:
    global _resolver
    if _resolver is None:
        _resolver = HostResolver()
    return _resolver
