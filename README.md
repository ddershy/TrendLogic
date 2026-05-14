# TrendLogic

TrendLogic 是一个面向电商运营场景的对话式 Multi-Agent AI 工作台。MVP 已包含用户注册/登录、角色权限、智能运营台、Agent trace 展示、最新爆品、基础用户画像和一键召回接口。

## 目录结构

```text
frontend/        Vue + TypeScript 智能运营工作台
backend/         Django JSON API、鉴权、会话、admin 和数据模型
agents/          Router / Requirement / ProductConsultant 等 Agent 与 LangGraph 编排
rag/             文档加载、chunk、embedding、LanceDB 向量检索
mcp/             本地工具注册层，统一封装 RAG、爆品库、用户工作台等工具
memory/          用户短期记忆、长期画像、会话摘要和记忆写入服务
metrics/         运行时指标、RAG 评测、性能测试结果
scripts/         初始化、性能测试、RAG 评测集播种等工程脚本
docs/            架构、API、部署、Agent 和记忆设计文档
deployment/      Nginx / systemd / Docker 等部署配置
uploads/         用户上传资料和 RAG 原始文档
```

## 后端运行

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py seed_trendlogic
python manage.py createsuperuser
python manage.py runserver 8000
```

后端默认地址：`http://localhost:8000`

Django 可视化管理后台：`http://localhost:8000/admin/`

后台账号使用 `createsuperuser` 创建，用于增删改查用户、爆品、分类、聊天记录、用户画像、上传文档和召回记录。

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
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
ADMIN_INVITE_CODE=trendlogic-admin
```

注册 admin 用户时，在注册表单填写 `ADMIN_INVITE_CODE` 对应的邀请码。

## 已实现能力

- 用户注册、登录、`account_id` 自动生成。
- Django 签名 Token 鉴权和 `normal_user` / `admin` 角色。
- 后端强制 admin 权限校验。
- 智能运营台 `/chat`，展示 trace 消息和 final 回复。
- 规则版 `RouterAgent`、`RequirementAgent`、`ProductConsultantAgent`。
- 最新爆品 `/trending`，支持公开条目上传。
- admin 用户洞察和一键召回基础接口及页面。
- RAG、MCP、Agent tools 独立目录和可替换接口。
- RAG 检索评测，支持 `precision@k`、`recall@k`、`MRR` 和平均检索延迟统计。
- 运行时指标埋点，记录 `chat.e2e`、`agent.node`、`rag.search` 等耗时。

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

## 当前流程架构

```text
TrendLogicGraph
  |
  +-- RouterAgent
  |     识别是否为电商运营问题，并判断任务类型
  |
  +-- RequirementAgent
  |     抽取平台、类目、预算、目标用户、内容形式、定价问题等结构化需求
  |
  +-- ProductConsultantAgent
        |
        +-- MCPToolClient
        |     |
        |     +-- RAGService.search()
        |     |     |
        |     |     +-- Query Embedding
        |     |     |
        |     |     +-- LanceDB Vector Search
        |     |
        |     +-- TrendingItem / UserWorkspace / RecallRecord 等工具
        |
        +-- LLM Provider
              结合结构化需求、RAG 资料、爆品库和用户记忆生成最终建议
  |
  +-- MemoryAgent
  |     写入用户消息、助手回复、trace、记忆候选
  |
返回 messages 给前端
```

## 后续计划

优化端到端与RAG召回质量
- 将 Router、Requirement、Consultant 的串行模型调用优化为更少的结构化 LLM 调用，降低网络往返和 token 消耗。
- 继续完善 RAG 文档上传、向量化、评测集管理和检索质量对比流程。

### 端到端延迟优化

- 合并串行 LLM 调用：将 `RouterAgent` 和 `RequirementAgent` 合并为一次结构化输出，返回 intent、是否追问、requirement_profile 和 missing_fields，减少模型调用次数。
- 减少工具规划开销：常规场景直接执行 RAG 和爆品库检索；只有当问题涉及外部搜索、用户工作台或召回记录时，再触发工具规划。
- 精简 prompt 和上下文：只传必要的 `requirement_profile`、压缩后的 memory summary 和 top 3-4 个高相关 RAG chunk，避免传入完整会话和无关工具结果。
- 缓存稳定中间结果：缓存 LangGraph 编译结果、用户长期记忆摘要、热门 query 的 embedding 和 RAG 检索结果。
- 异步化非关键写入：将记忆总结、画像更新、指标写入等非阻塞任务放到后台队列，接口优先返回最终回复。
- 优化流式响应：`/api/chat/message/stream` 优先返回 session、process trace 和首段内容，用 `first_token_ms` 衡量用户感知等待。
- 增加超时、重试和熔断：为 LLM、embedding、搜索工具设置独立超时；外部服务异常时返回可解释的降级结果，并记录失败原因。
- 替换生产数据库：SQLite 适合 MVP，本地并发写入会导致尾延迟；生产环境改为 PostgreSQL，并为 session、metric、memory 表增加必要索引。

### RAG 命中率优化

- 建立固定评测集：维护 10-30 条人工标注 `RAGEvaluationCase`，每条包含 query、期望文档、期望关键词和 top_k，用 `precision@k`、`recall@k`、`MRR` 和 `avg_latency_ms` 对比调整效果。
- 调整 chunk 策略：按标题、段落和语义边界切分，避免把多个主题混进同一 chunk；对长文档保留 heading/path 元数据。
- 增加 metadata filter：检索时按 category、visibility、uploaded_by、平台或业务场景过滤，减少无关文档进入 top_k。
- 引入 rerank：先向量召回 top 20，再用关键词匹配、BM25 或 reranker 重新排序，提升 `precision@k` 和 MRR。
- 混合检索：结合向量相似度和关键词召回，解决专有名词、价格、平台名、商品名这类 embedding 容易漂移的问题。
- 查询改写：将用户问题改写成包含平台、类目、任务类型和关键约束的检索 query，提高召回稳定性。
- 观察指标联动：每次调整后同时比较 `precision@k`、`recall@k`、`MRR`、`avg_latency_ms`，只保留质量提升且延迟可接受的方案。

### Token 成本评估

- 在 LLMClient 中记录每次调用的 `prompt_tokens`、`completion_tokens`、`total_tokens`、模型名、agent 名和 request_id。
- 按请求聚合 `tokens/request`，拆分 router、requirement、tool planner、consultant 四类 token 消耗。
- 以当前串行链路为 baseline，对比“合并 router + requirement”“关闭不必要 tool planner”“压缩 RAG context”后的 token 消耗变化。
- 目标是通过减少 LLM 调用次数和缩短 prompt，将平均 `tokens/request` 降低 30%-50%，最终以 provider usage 日志和本地 MetricEvent 双重校验。
