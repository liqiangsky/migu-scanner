# Migu TV Proxy

TV 直播代理系统，从数据源 URL 解析 HOST，根据地区选择最佳节点，提供频道代理服务。

## 功能

- 从配置的数据源 URL 自动拉取并解析 HOST
- 支持 `http(s)://HOST/\d{9}` 格式的 URL 解析
- 基于 ip2region 获取 HOST 归属地信息
- 定时复测 HOST 有效性，自动清理无效节点
- 根据用户地区智能选择最佳 HOST
- 播放地址缓存，减少重复请求
- 前端可视化配置管理

## 目录结构

```
migu/
├── backend/              # Python FastAPI 后端
│   ├── app.py           # 主应用
│   ├── config.py        # 配置
│   ├── database.py      # 数据库
│   ├── models.py        # 数据模型
│   ├── services/        # 服务层
│   │   ├── url_parser.py     # URL 解析
│   │   ├── host_resolver.py  # HOST 解析 + 归属地
│   │   ├── cache_service.py  # 缓存服务
│   │   └── channel_service.py # 频道代理
│   └── data/            # 数据目录
├── frontend/            # Vue3 前端
│   ├── src/
│   │   ├── views/       # 页面组件
│   │   └── App.vue      # 根组件
│   └── vite.config.js   # Vite 配置
├── channel.txt          # 频道列表模板
├── source.txt           # 初始数据源（可选）
├── docker-compose.yml   # Docker 编排
└── README.md
```

## 端口说明

- **后端 API**: 1847
- **播放代理**: 2847
- **前端开发**: 3000

## Docker 构建说明

支持国内镜像加速，构建时传入参数：

```bash
# 使用 DaoCloud 镜像加速
docker build --build-arg BASE_REGISTRY=docker.m.daocloud.io -t migu-backend ./backend
docker build --build-arg BASE_REGISTRY=docker.m.daocloud.io --build-arg NPM_REGISTRY=https://registry.npmmirror.com -t migu-frontend ./frontend

# 或使用 docker-compose
BASE_REGISTRY=docker.m.daocloud.io docker-compose build
docker-compose up -d
```

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| BASE_REGISTRY | Docker 基础镜像源 | docker.io |
| REGISTRY_MIRROR | pip 镜像源 | 无 |
| APT_MIRROR | apt 镜像源 | mirrors.aliyun.com |
| NPM_REGISTRY | npm 镜像源 | https://registry.npmmirror.com |

## 快速开始

### 使用 Docker Compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 本地开发

#### 后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

访问 http://localhost:1847/docs 查看 API 文档

#### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## API 接口

### 数据源管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sources | 获取数据源列表 |
| POST | /api/sources | 添加数据源 |
| DELETE | /api/sources/{id} | 删除数据源 |
| PUT | /api/sources/{id}/toggle | 切换启用状态 |

### HOST 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/hosts | 获取 HOST 列表（支持地区筛选） |
| DELETE | /api/hosts/{id} | 删除 HOST |
| POST | /api/pull | 手动触发拉取 |
| POST | /api/test | 手动触发复测 |

### 播放列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /playlist.m3u | 获取 m3u 播放列表 |
| GET | /playlist.m3u8 | 获取 m3u8 播放列表 |

### 频道代理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /proxy/{code} | 代理频道播放 |
| GET | /api/channels | 获取频道列表 |

### 配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/config | 获取配置 |
| PUT | /api/config/cache_ttl | 更新缓存时间 |

### 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/stats | 获取统计信息 |

## 播放流程

### 单频道代理
1. 客户端访问 `http://localhost:2847/608807420`
2. 服务端根据请求头 `X-Region` 或默认地区查找 HOST
3. 优先选择同地区 HOST，否则选择延迟最低的
4. 向选定的 HOST 发起请求，获取 302 重定向
5. 缓存结果（key=频道CODE）
6. 返回 302 重定向给客户端

示例：
```
http://localhost:2847/proxy/608807420
  -> http://166.52.6.60:8864/608807420
  -> 302 -> 最终播放地址
```

### 播放列表
1. 客户端访问 `http://localhost:2847/playlist.m3u`
2. 服务端读取 channel.txt，生成 m3u 格式播放列表
3. 每个频道的 URL 指向代理端点 `/{code}`
4. 用 VLC、IPTV 播放器等打开即可观看

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| MIGU_CACHE_TTL | 10800 | 缓存时间（秒） |
| MIGU_PULL_INTERVAL | 3600 | 拉取间隔（秒） |
| MIGU_TEST_INTERVAL | 1800 | 复测间隔（秒） |

### channel.txt 格式

```
频道名称,http://HOST/9位数字CODE
```

示例：
```
CCTV1综合,http://HOST/608807420
CCTV2财经,http://HOST/631780532
```

## License

MIT
