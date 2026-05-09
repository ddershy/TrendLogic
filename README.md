# TrendLogic

TrendLogic 是一个面向电商运营场景的对话式 Multi-Agent AI 工作台。MVP 已包含用户注册/登录、角色权限、智能运营台、Agent trace 展示、最新爆品、基础用户画像和一键召回接口。

## 目录结构

```text
frontend/   React + TypeScript 工作台
backend/    FastAPI + SQLAlchemy + SQLite API
agents/     Multi-Agent 定义、编排与工具
rag/        独立 RAG 模块占位，后续替换 LanceDB
mcp/        工具注册层，后续接入 MCP
docs/       架构、API、Agent 和记忆设计文档
```

## 后端运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
python -m uvicorn backend.app.main:app --reload
```

后端默认地址：`http://localhost:8000`

## 前端运行

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## 环境变量

复制 `.env.example` 并按需调整。MVP 默认使用 SQLite：

```text
DATABASE_URL=sqlite:///./trendlogic.db
JWT_SECRET=replace-with-a-long-random-secret
ADMIN_INVITE_CODE=trendlogic-admin
```

注册 admin 用户时，在注册表单填写 `ADMIN_INVITE_CODE` 对应的邀请码。

## 已实现能力

- 用户注册、登录、`account_id` 自动生成。
- JWT 鉴权和 `normal_user` / `admin` 角色。
- 后端强制 admin 权限校验。
- 智能运营台 `/chat`，展示 trace 消息和 final 回复。
- 规则版 `RouterAgent`、`RequirementAgent`、`ProductConsultantAgent`。
- 最新爆品 `/trending`，支持公开条目上传。
- admin 用户洞察和一键召回基础接口及页面。
- RAG、MCP、Agent tools 独立目录和可替换接口。

## 关键接口

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/chat/message`
- `GET /api/trending`
- `POST /api/trending`
- `GET /api/admin/user-insights`
- `GET /api/recall/candidates`
- `POST /api/recall/generate`

## 后续计划

- 将规则版 Agent 替换为可配置 LLM Provider。
- 将 RAG 的本地向量存储替换为 LanceDB。
- 补齐 admin 爆品管理编辑界面和内部文档向量化流程。
- 增加 Alembic 迁移、自动化测试和会话摘要任务。
