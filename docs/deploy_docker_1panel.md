# TrendLogic Docker + 1Panel 部署

目标：

```text
代码目录：/home/zqy/app/TrendLogic
前端目录：/opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index
域名：https://trendlogic.dershy.top/
后端容器：127.0.0.1:8000
```

架构：

```text
1Panel OpenResty
├── /        -> Vue dist 静态文件
├── /api/    -> http://127.0.0.1:8000
├── /admin/  -> http://127.0.0.1:8000
└── /static/ -> /home/zqy/app/TrendLogic/backend/staticfiles

Docker Compose
└── trendlogic-backend -> Django + Gunicorn
```

## 1. 上传代码

服务器目录：

```bash
mkdir -p /home/zqy/app/TrendLogic
cd /home/zqy/app/TrendLogic
```

把本地项目代码同步到这个目录。

不要上传：

```text
.env
backend/.venv
frontend/node_modules
frontend/dist
data
uploads
lancedb
*.sqlite3
```

## 2. 创建 .env

```bash
cd /home/zqy/app/TrendLogic
cp .env.production.example .env
nano .env
```

Docker Compose 会覆盖下面两个路径，所以 `.env` 里可以写，也可以不写：

```env
DJANGO_DATABASE_NAME=/app/data/db.sqlite3
LANCEDB_URI=/app/data/lancedb
```

生产必须确认：

```env
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=trendlogic.dershy.top,47.94.11.159,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://trendlogic.dershy.top
CORS_ORIGINS=https://trendlogic.dershy.top
```

同时填写：

```env
DJANGO_SECRET_KEY=
ADMIN_INVITE_CODE=
LLM_BASE_URL=
LLM_MODEL=
LLM_API_KEY=
MEMORY_MODEL=
SUMMARY_MODEL=
DASHSCOPE_API_KEY=
SERPAPI_API_KEY=
```

## 3. 构建并启动后端容器

```bash
cd /home/zqy/app/TrendLogic
docker compose build backend
docker compose up -d backend
```

初始化数据库和静态文件：

```bash
docker compose exec backend bash scripts/docker-init-backend.sh
```

查看日志：

```bash
docker compose logs -f backend
```

检查端口：

```bash
curl http://127.0.0.1:8000/health
```

## 4. 构建前端

前端可以在服务器构建：

```bash
cd /home/zqy/app/TrendLogic/frontend
npm install
VITE_API_BASE_URL=https://trendlogic.dershy.top/api npm run build
```

复制到 1Panel 网站 root：

```bash
rm -rf /opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index/*
cp -r /home/zqy/app/TrendLogic/frontend/dist/* /opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index/
```

## 5. 配置 1Panel 反向代理

1Panel 网站已经绑定：

```text
trendlogic.dershy.top
```

网站 root：

```text
/opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index
```

需要配置：

```text
/api/    -> http://127.0.0.1:8000
/admin/  -> http://127.0.0.1:8000
```

建议在 OpenResty 自定义配置里保证：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /admin/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /static/ {
    alias /home/zqy/app/TrendLogic/backend/staticfiles/;
}
```

如果 1Panel 管理 Nginx 配置，请在面板里添加反向代理和静态目录，不要手动破坏证书配置。

## 6. 更新发布

```bash
cd /home/zqy/app/TrendLogic
docker compose build backend
docker compose up -d backend
docker compose exec backend bash scripts/docker-init-backend.sh

cd /home/zqy/app/TrendLogic/frontend
npm install
VITE_API_BASE_URL=https://trendlogic.dershy.top/api npm run build
rm -rf /opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index/*
cp -r dist/* /opt/1panel/apps/openresty/openresty/www/sites/trendlogic.dershy.top/index/
```

## 7. 排错

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend python backend/manage.py check
curl http://127.0.0.1:8000/health
```
