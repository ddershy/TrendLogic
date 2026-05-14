# TrendLogic ECS 部署指南

目标域名：

```text
https://trendlogic.dershy.top/
```

推荐部署结构：

```text
Nginx 443
├── /                -> Vue dist
├── /api/            -> Django Gunicorn 127.0.0.1:8000
├── /admin/          -> Django Admin
└── /static/         -> Django collectstatic
```

项目目录：

```text
/var/www/trendlogic
```

## 1. DNS 与安全组

在域名 DNS 控制台添加：

```text
A  trendlogic.dershy.top  -> ECS 公网 IP
```

ECS 安全组放行：

```text
22    SSH
80    HTTP
443   HTTPS
```

## 2. 安装系统依赖

Ubuntu/Debian：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git curl nodejs npm certbot python3-certbot-nginx
```

如果系统自带 Node 版本太低，建议安装 Node 20：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 3. 上传代码

方式一：服务器直接拉 Git 仓库：

```bash
sudo mkdir -p /var/www
sudo chown -R $USER:$USER /var/www
git clone <your-repo-url> /var/www/trendlogic
cd /var/www/trendlogic
```

方式二：本地 rsync/scp 上传代码到 `/var/www/trendlogic`。

不要上传：

```text
.env
backend/.venv
frontend/node_modules
frontend/dist
uploads
lancedb
*.sqlite3
```

这些已经由 `.gitignore` 保护。

## 4. 配置后端环境

```bash
cd /var/www/trendlogic
cp .env.production.example .env
nano .env
```

至少确认：

```env
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=trendlogic.dershy.top,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://trendlogic.dershy.top
CORS_ORIGINS=https://trendlogic.dershy.top
DJANGO_DATABASE_NAME=/var/www/trendlogic/backend/db.sqlite3

LLM_BASE_URL=...
LLM_MODEL=...
LLM_API_KEY=...

DASHSCOPE_API_KEY=...
LANCEDB_URI=/var/www/trendlogic/lancedb
```

## 5. 安装 Python 依赖

```bash
cd /var/www/trendlogic
python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements.txt
```

## 6. 初始化数据库与静态文件

项目当前关闭了 Django migrations，所以使用 `--run-syncdb` 和自定义升级命令：

```bash
cd /var/www/trendlogic
backend/.venv/bin/python backend/manage.py migrate --run-syncdb
backend/.venv/bin/python backend/manage.py upgrade_chat_storage
backend/.venv/bin/python backend/manage.py upgrade_memory_storage
backend/.venv/bin/python backend/manage.py upgrade_rag_storage
backend/.venv/bin/python backend/manage.py upgrade_metrics_storage
backend/.venv/bin/python backend/manage.py collectstatic --noinput
backend/.venv/bin/python backend/manage.py check
```

创建 admin：

```bash
backend/.venv/bin/python backend/manage.py shell
```

在 shell 中执行：

```python
from core.models import User
User.objects.create(account_id="admin", display_name="admin", password_hash="your-password", role="admin")
```

## 7. 构建前端

```bash
cd /var/www/trendlogic/frontend
npm install
VITE_API_BASE_URL=https://trendlogic.dershy.top/api npm run build
```

## 8. 配置 systemd

```bash
sudo cp /var/www/trendlogic/deployment/systemd/trendlogic-backend.service /etc/systemd/system/trendlogic-backend.service
sudo systemctl daemon-reload
sudo systemctl enable trendlogic-backend
sudo systemctl start trendlogic-backend
sudo systemctl status trendlogic-backend
```

查看日志：

```bash
sudo journalctl -u trendlogic-backend -f
```

## 9. 配置 Nginx 与 HTTPS

先申请证书：

```bash
sudo mkdir -p /var/www/certbot
sudo nginx -t
sudo systemctl reload nginx
sudo certbot certonly --nginx -d trendlogic.dershy.top
```

复制配置：

```bash
sudo cp /var/www/trendlogic/deployment/nginx/trendlogic.conf /etc/nginx/sites-available/trendlogic.conf
sudo ln -sf /etc/nginx/sites-available/trendlogic.conf /etc/nginx/sites-enabled/trendlogic.conf
sudo nginx -t
sudo systemctl reload nginx
```

打开：

```text
https://trendlogic.dershy.top/
https://trendlogic.dershy.top/admin/
```

## 10. 发布更新

```bash
cd /var/www/trendlogic
git pull
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python backend/manage.py migrate --run-syncdb
backend/.venv/bin/python backend/manage.py upgrade_chat_storage
backend/.venv/bin/python backend/manage.py upgrade_memory_storage
backend/.venv/bin/python backend/manage.py upgrade_rag_storage
backend/.venv/bin/python backend/manage.py upgrade_metrics_storage
backend/.venv/bin/python backend/manage.py collectstatic --noinput

cd /var/www/trendlogic/frontend
npm install
VITE_API_BASE_URL=https://trendlogic.dershy.top/api npm run build

sudo systemctl restart trendlogic-backend
sudo nginx -t
sudo systemctl reload nginx
```

## 11. 常见排错

后端服务：

```bash
sudo systemctl status trendlogic-backend
sudo journalctl -u trendlogic-backend -n 100 --no-pager
```

Nginx：

```bash
sudo nginx -t
sudo tail -n 100 /var/log/nginx/error.log
```

Django 配置：

```bash
cd /var/www/trendlogic
backend/.venv/bin/python backend/manage.py check
```

端口：

```bash
ss -lntp | grep 8000
```

RAG：

```bash
backend/.venv/bin/python backend/manage.py shell
```

```python
from rag import RAGService
RAGService().search("小红书选品", top_k=3)
```
