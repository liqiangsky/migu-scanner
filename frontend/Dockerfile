# ==========================================
# 前端 Dockerfile
# 构建: docker build -t migu-frontend .
# 运行: docker run -d --name migu-frontend -p 3000:80 migu-frontend
# 国内镜像加速: docker build --build-arg BASE_REGISTRY=docker.m.daocloud.io .
# ==========================================

# 基础镜像 registry（国内用户可改为 docker.m.daocloud.io 等镜像源）
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/node:20-alpine AS builder

# 国内 npm 镜像加速
ARG NPM_REGISTRY=https://registry.npmmirror.com

WORKDIR /app
COPY package.json package-lock.json* ./

RUN npm config set registry ${NPM_REGISTRY} && npm install

COPY . .
RUN npm run build

# 第二阶段
ARG BASE_REGISTRY=docker.io
FROM ${BASE_REGISTRY}/library/nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
