import re
import logging

logger = logging.getLogger("migu.channel_parser")


def parse_m3u(content: str) -> list[dict]:
    """解析 m3u/m3u8 格式 (#EXTINF 行 + URL)"""
    lines = content.split('\n')
    result = []
    current_channel = None

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        # EXTINF 行: #EXTINF:-1 group-title="分组",频道名称
        if trimmed.startswith('#EXTINF'):
            group_match = re.search(r'group-title="([^"]*)"', trimmed)
            last_comma_idx = trimmed.rfind(',')
            name = trimmed[last_comma_idx + 1:].strip() if last_comma_idx > 0 else f'频道{len(result) + 1}'

            current_channel = {
                'name': name or f'频道{len(result) + 1}',
                'group': group_match.group(1).strip() if group_match else '',
                'url': ''
            }
            continue

        # 注释行跳过
        if trimmed.startswith('#'):
            continue

        # URL 行（非注释，且有上一个 EXTINF）
        if current_channel:
            if not trimmed or len(trimmed) < 5:
                current_channel = None
                continue
            url = trimmed
            dollar_idx = url.find('$')
            if dollar_idx > 0:
                url = url[:dollar_idx].strip()
            current_channel['url'] = url
            result.append(current_channel)
            current_channel = None

    return result


def parse_txt(content: str) -> list[dict]:
    """解析 txt/genre 格式 (名称,#genre# 分组 + 频道名,url 条目)"""
    lines = content.split('\n')
    result = []
    current_group = '未分组'

    for line in lines:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith('#'):
            continue

        # 分组行：名称,#genre#
        if trimmed.lower().endswith(',#genre#'):
            group_name = trimmed.replace(',#genre#', '').strip()
            if group_name:
                current_group = group_name
            continue

        # 频道行：必须包含英文逗号，且逗号后是有效的 URL
        comma_idx = trimmed.find(',')
        if comma_idx <= 0:
            continue

        name = trimmed[:comma_idx].strip()
        url = trimmed[comma_idx + 1:].strip()

        # 跳过不符合格式的行
        if not name or not url:
            continue
        if not re.match(r'^https?://', url) and not re.match(r'^/', url):
            continue

        # 去除 URL 末尾的 $备注 部分
        dollar_idx = url.find('$')
        if dollar_idx > 0:
            url = url[:dollar_idx].strip()

        result.append({'name': name, 'group': current_group, 'url': url})

    return result


def detect_and_parse(content: str, filename: str = '') -> list[dict]:
    """自动检测文件格式并解析"""
    lower_content = content.lower()
    lower_name = filename.lower()

    # 根据文件扩展名或内容特征判断格式
    if lower_name.endswith('.m3u') or lower_name.endswith('.m3u8') or '#extinf' in lower_content:
        return parse_m3u(content)
    return parse_txt(content)


def filter_migu_channels(channels: list[dict]) -> list[dict]:
    """过滤只保留 Migu 格式的频道（URL以 /9位数字 结尾）"""
    pattern = re.compile(r'/\d{9}$')
    return [ch for ch in channels if pattern.search(ch.get('url', ''))]


def extract_code(url: str) -> str | None:
    """提取频道 CODE（URL 末尾的 9 位数字）"""
    match = re.search(r'/(\d{9})$', url)
    return match.group(1) if match else None
