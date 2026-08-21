# ==========================================
# 后端 Dockerfile
# 构建: docker build -t migu-backend .
# 运行: docker run -d --name migu-backend -p 1847:8000 -p 2847:2847 migu-backend
# 国内镜像加速: docker build --build-arg BASE_REGISTRY=docker.m.daocloud.io .
# ==========================================

# 基础镜像 registry（国内用户可改为 docker.m.daocloud.io 等镜像源）
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/python:3.11-slim-bookworm

# 国内镜像加速（构建时传入，仅对 pip 安装生效）
# 使用: docker build --build-arg REGISTRY_MIRROR=https://pypi.doubanio.com/simple .
ARG REGISTRY_MIRROR
RUN if [ -n "$REGISTRY_MIRROR" ]; then \
        pip config set global.index-url "$REGISTRY_MIRROR"; \
    fi

# Debian 镜像源（国内用户可设为 mirrors.aliyun.com 或 mirrors.tuna.tsinghua.edu.cn）
# 使用: docker build --build-arg APT_MIRROR=mirrors.aliyun.com .
ARG APT_MIRROR
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s|deb.debian.org|$APT_MIRROR|g" /etc/apt/sources.list; \
    fi

WORKDIR /app

# 安装运行时工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝后端代码
COPY . /app/

# 下载 ip2region 离线数据库（本地已有则覆盖，确保最新）
RUN mkdir -p /app/data && \
    curl -fSL -o /app/data/ip2region_v4.xdb \
    "https://gh-proxy.org/https://raw.githubusercontent.com/lionsoul2014/ip2region/master/data/ip2region_v4.xdb" || \
    echo "⚠️ curl 下载 xdb 失败，使用本地文件（如有）"

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 数据目录
ENV DB_PATH=/app/data/migu.db

RUN mkdir -p /app/data

EXPOSE 8000 2847

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "2847"]
