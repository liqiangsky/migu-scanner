import re
import asyncio
import aiohttp
import logging
from typing import List, Set, Tuple, Optional, Callable
from config import settings

logger = logging.getLogger("migu.parser")


async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """获取URL内容"""
    # 确保 URL 有协议前缀
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    try:
        logger.info(f"Fetching URL: {url}")
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                content = await resp.text()
                logger.info(f"Successfully fetched {url}, content length: {len(content)}")
                return content
            else:
                logger.warning(f"Failed to fetch {url}, status code: {resp.status}")
                return ""
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching URL: {url}")
        return ""
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}", exc_info=True)
        return ""


def parse_urls_from_content(content: str) -> Set[str]:
    """
    从内容中解析 URL，匹配格式: http(s)://HOST[:PORT]/.../9位数字
    只要路径以9位数字结尾就算有效
    返回: URL 集合
    """
    # 匹配完整URL（包含9位数字）
    # [^\s#$]* 贪婪匹配URL主体（不含空白、#、$）
    # /\d{9} 确保以 /9位数字 结尾
    # (?=[#$\r\n]|$) 确保9位数字后是$、#、换行或字符串结束
    pattern = r'https?://[^\s#$]*/\d{9}(?=[#$\r\n]|$)'
    matches = re.findall(pattern, content)

    urls = set()
    for url in matches:
        urls.add(url)

    logger.debug(f"Parsed {len(urls)} unique URLs from content")
    return urls


def deduplicate_urls(urls: Set[str]) -> List[str]:
    """
    用 999999999 替换 URL 末尾的9位数字进行去重
    返回: 去重后的 URL 列表
    """
    placeholder = "999999999"
    dedup_set = set()
    for url in urls:
        # 替换末尾的9位数字为占位符
        dedup_url = re.sub(r'\d{9}(?!\d)$', placeholder, url)
        dedup_set.add(dedup_url)

    logger.debug(f"Deduplicated {len(urls)} URLs to {len(dedup_set)} unique URLs")
    return list(dedup_set)


async def parse_all_sources(
    sources: List[dict],
    on_progress: Optional[Callable] = None
) -> List[str]:
    """
    解析所有数据源，返回去重后的 URL 列表
    去重规则：用 999999999 替换末尾9位数字后去重
    返回: [url1, url2, ...]
    """
    all_urls: Set[str] = set()

    enabled_sources = [s for s in sources if s.get('enabled', True)]
    urls = [s['url'] for s in enabled_sources]

    logger.info(f"Starting parse for {len(urls)} enabled sources")

    if not urls:
        logger.warning("No enabled source URLs")
        return []

    if on_progress:
        await on_progress("parsing_start", {"total": len(urls)})

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url_content(session, url) for url in urls]
        contents = await asyncio.gather(*tasks, return_exceptions=True)

    for i, content in enumerate(contents):
        url = urls[i]
        if isinstance(content, Exception):
            logger.error(f"Error fetching {url}: {content}")
            if on_progress:
                await on_progress("source_error", {"index": i + 1, "total": len(urls), "url": url, "error": str(content)})
            continue

        if content:
            parsed_urls = parse_urls_from_content(content)
            all_urls.update(parsed_urls)
            logger.info(f"Source {i+1}/{len(urls)} ({url}): found {len(parsed_urls)} URLs")
            if on_progress:
                await on_progress("source_parsed", {"index": i + 1, "total": len(urls), "hosts_found": len(parsed_urls), "url": url})
        else:
            logger.warning(f"Source {i+1}/{len(urls)} ({url}): empty or failed")
            if on_progress:
                await on_progress("source_empty", {"index": i + 1, "total": len(urls), "url": url})

    # URL级别去重
    unique_urls = deduplicate_urls(all_urls)
    logger.info(f"Total unique URLs after deduplication: {len(unique_urls)}")
    if on_progress:
        await on_progress("parsing_done", {"total_hosts": len(unique_urls)})

    return unique_urls
