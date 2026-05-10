# TrendLogic 项目开发 Prompt

> 适用对象：Codex / Copilot Coding Agent / Cursor Agent / 其他代码执行型 Agent  
> 项目定位：面向电商运营场景的 Multi-Agent AI 系统  
> 推荐使用方式：将本文档作为项目根目录下的 `CODEX_PROJECT_PROMPT.md`，并让代码 Agent 逐步执行。

---

## 0. 执行原则

你是一个专业的全栈代码编写、架构设计与代码审查 Agent。你需要基于用户需求，逐步完成一个面向电商运营场景的 Multi-Agent AI 系统，项目名称为 **TrendLogic**。

你的工作目标不是简单生成零散代码，而是像一名高级工程师一样，先理解需求、分析现有项目结构、制定开发计划，然后以模块化、可维护、可扩展的方式逐步实现功能。

你被允许新增、修改、重构当前项目下的所有文件，但必须遵守以下原则：

1. 不要盲目覆盖已有文件，修改前先阅读现有代码结构。
2. 每次修改前说明你打算修改哪些文件、为什么修改。
3. 每个阶段完成后要进行自检，包括：
   - 是否满足需求；
   - 是否有明显 bug；
   - 是否有未实现接口；
   - 是否有前后端字段不一致；
   - 是否有权限控制遗漏。
4. 所有代码应尽量模块化，便于后续接入 Skills 工程、Agent Harness 工程、MCP、RAG、Function Calling 等能力。
5. RAG 和 MCP 应设计为独立通用模块，不要和具体业务强耦合。
6. RAG 默认使用 LanceDB 作为向量数据库，但 Embedding 模型和大模型供应商必须可配置、可替换。
7. 当前项目应优先完成一个可运行的 MVP，然后再逐步增强。
8. 如果发现用户需求中存在不合理或可优化的地方，可以主动提出更优方案，但不能偏离 TrendLogic 的核心业务目标。

---

## 1. 小步开发方式

你不要直接一次性生成大量不可运行的代码。你必须采用“小步提交”的方式开发。

每一步都要遵循：

```text
Read → Plan → Modify → Test → Explain
```

也就是：

1. 先读取已有项目文件；
2. 再制定本轮修改计划；
3. 然后修改代码；
4. 尝试运行或静态检查；
5. 最后解释本轮完成内容。

如果你发现当前项目缺少依赖、缺少配置或存在冲突，请优先修复工程可运行性。

每一轮修改后都需要说明：

- 修改了哪些文件；
- 新增了哪些能力；
- 如何运行；
- 如何测试；
- 还有哪些待完成事项。

---

## 2. 项目定位

TrendLogic 是一个面向电商运营的对话式 AI Multi-Agent 系统。

它的核心目标是帮助电商用户进行：

1. 选品咨询；
2. 流量趋势分析；
3. 热点爆品发现；
4. 带货内容建议；
5. 用户长期画像维护；
6. 老用户智能召回。

系统不是普通聊天机器人，而是一个 **AI 电商运营助手平台**。

用户通过前端页面与 AI 对话，系统根据用户输入自动路由到不同 Agent，并在必要时展示 Agent 的执行日志、任务流转和最终回复。

注意：

- 可以展示 Agent 的可解释执行日志；
- 不要展示模型真实链式思考；
- 执行日志应该是面向用户可读的过程说明，例如：

```text
[分类决策Agent/意图识别] 用户问题属于选品咨询场景，准备进入需求分析流程。
[需求分析Agent/需求补全] 用户尚未说明目标平台和预算，需要继续追问。
```

---

## 3. 推荐技术栈

请根据现有项目结构判断当前技术栈。如果项目尚未初始化，则优先采用以下技术栈。

### 前端

- Vue
- TypeScript
- Vite
- CSS Modules / Tailwind CSS 可选
- Pinia 或 Vue Composition API 管理状态

### 后端

- Python
- Django
- Django ORM
- Django JSON API 或 Django REST Framework 可选
- Django migrations
- PostgreSQL 或 SQLite 开发环境
- Redis 可作为后续缓存/任务队列

### AI / Agent

- OpenAI / DeepSeek / Qwen 等模型接口可配置
- Function Calling 工具调用
- Multi-Agent Orchestrator 自研轻量实现，后续可接入 LangGraph / AutoGen / CrewAI
- RAG 使用 LanceDB
- Embedding 模型可配置
- MCP 作为独立 tools 接入层预留

### 工程结构

- `frontend/` 存放前端代码
- `backend/` 存放后端代码
- `agents/` 存放 Agent 定义、编排和工具调用逻辑
- `rag/` 或 `backend/rag/` 存放 RAG 模块
- `mcp/` 或 `backend/mcp/` 存放 MCP 工具适配模块
- `docs/` 存放项目文档

---

## 4. 建议目录结构

请尽量将项目组织为以下结构。如果当前已有结构，请在不破坏现有功能的基础上逐步调整。

```text
TrendLogic/
├── frontend/
│   ├── src/
│   │   ├── app/ 或 pages/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   ├── auth/
│   │   │   ├── trending/
│   │   │   ├── user-profile/
│   │   │   └── recall/
│   │   ├── api/
│   │   ├── stores/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
│
├── backend/
│   ├── manage.py
│   ├── trendlogic_backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── core/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── middleware.py
│   │   └── management/
│   └── requirements.txt
│
├── agents/
│   ├── orchestrator.py
│   ├── base_agent.py
│   ├── router_agent.py
│   ├── requirement_agent.py
│   ├── product_consultant_agent.py
│   ├── user_profile_agent.py
│   ├── user_recall_agent.py
│   ├── prompts/
│   │   ├── router_agent.md
│   │   ├── requirement_agent.md
│   │   ├── product_consultant_agent.md
│   │   ├── user_profile_agent.md
│   │   └── user_recall_agent.md
│   └── tools/
│       ├── search_tool.py
│       ├── rag_tool.py
│       ├── database_tool.py
│       └── trend_tool.py
│
├── rag/
│   ├── vector_store.py
│   ├── embedder.py
│   ├── retriever.py
│   ├── document_loader.py
│   ├── chunker.py
│   └── config.py
│
├── mcp/
│   ├── client.py
│   ├── registry.py
│   └── tools/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── agent_workflow.md
│   └── memory_design.md
│
├── README.md
└── .env.example
```

---

## 5. 前端页面需求

TrendLogic 前端需要提供一个面向用户的 AI 电商运营工作台。

用户进入前端页面后，应弹窗询问是否登录。

如果用户未登录：

- 可以看到登录/注册入口；
- 不允许使用核心功能。

如果用户登录后：

- 可以进入默认对话页面；
- 可以查看“最新爆品”；
- 普通用户不能访问 admin 功能；
- admin 用户可以访问用户洞察和一键召回页面。

---

### 5.1 智能运营台

原始需求中的“默认对话”页面建议命名为：

```text
智能运营台
```

英文路由建议：

```text
/chat
```

这是用户和 TrendLogic AI 交流的核心界面。

用户输入问题后，系统会：

1. 接收用户输入；
2. 调用分类决策 Agent 判断问题类型；
3. 如果属于平台业务范围，则路由给对应 Agent；
4. 如果用户需求不清晰，则交给需求分析 Agent 继续追问；
5. 如果需求已明确，则交给选品咨询 Agent、流量分析逻辑或带货建议逻辑；
6. 在对话区域展示 Agent 工作过程；
7. 最终以正常 AI 对话气泡显示回复用户的结果。

Agent 执行日志展示方式：

```text
[分类决策Agent/意图识别] 用户问题属于选品咨询场景，准备进入需求分析流程。
[需求分析Agent/需求补全] 用户尚未说明目标平台和预算，需要继续追问。
[选品咨询Agent/候选商品检索] 已从知识库和趋势库中检索到 5 个相关类目。
```

最终回复使用正常聊天气泡显示，例如：

```text
我已经理解你的需求。接下来我会先帮你明确目标人群、预算区间和销售平台，然后再给出更准确的选品建议。
```

---

### 5.2 最新爆品页面

页面名称：

```text
最新爆品
```

英文路由：

```text
/trending
```

该页面用于展示近期热点、爆品趋势和用户上传的热门内容。

内容来源包括：

1. AI 自动生成或推送的热点内容；
2. 普通用户主动上传的热点条目；
3. admin 用户上传的热点条目；
4. admin 用户上传的内部文档。

展示规则：

1. 普通热点条目可以显示在页面上；
2. 用户上传的公开内容可以显示在页面上；
3. admin 上传的公开内容可以显示在页面上；
4. admin 上传的内部文档不显示在主页；
5. admin 上传的内部文档需要进入 RAG 知识库，作为后续选品咨询 Agent 的检索依据。

每条爆品内容建议字段：

```text
- id
- title
- category
- source
- summary
- heat_score
- tags
- created_by
- created_at
- visibility: public / private_rag_only
- is_ai_generated
```

普通用户能力：

- 查看公开爆品；
- 上传自己认为热门的条目；
- 编辑或删除自己上传的条目。

admin 用户能力：

- 查看所有公开内容；
- 上传公开热点；
- 上传内部文档；
- 管理所有用户上传内容；
- 删除违规或无效内容；
- 将某些内容标记为 RAG 知识库素材。

---

### 5.3 用户洞察页面

原始名称“用户画像”建议优化为：

```text
用户洞察
```

英文路由：

```text
/user-insights
```

访问权限：

```text
仅 admin 可访问。
```

该页面展示系统对用户长期行为的总结，包括：

1. 用户经常关注的垂直领域；
2. 用户常问问题类型；
3. 用户偏好的平台，例如淘宝、抖音、小红书、TikTok、Amazon 等；
4. 用户关注的价格带；
5. 用户访问频率；
6. 最近一次访问时间；
7. 最近一次完整对话摘要；
8. 用户反馈偏好；
9. 推荐结果接受度；
10. 用户价值评分。

用户画像字段建议：

```text
- user_id
- display_name
- account_id
- preferred_categories
- preferred_platforms
- price_range_preference
- content_style_preference
- interaction_frequency
- last_active_at
- last_conversation_summary
- long_term_memory_summary
- interest_decay_map
- recall_score
- updated_at
```

---

### 5.4 一键召回页面

页面名称：

```text
一键召回
```

英文路由：

```text
/recall
```

访问权限：

```text
仅 admin 可访问。
```

该页面展示所有历史用户，并根据用户活跃度、历史偏好、最近热点匹配度等因素生成智能召回名单。

每个用户卡片应展示：

1. 用户名；
2. 自动生成账号；
3. 最近一次使用时间；
4. 最近一次关注内容；
5. 高频关注类目；
6. 召回优先级评分；
7. 推荐召回原因；
8. “生成召回口令”按钮。

点击“生成召回口令”后：

- 系统调用用户召回 Agent；
- 根据该用户历史画像、最近热点、相似用户行为和平台策略生成一段召回文案；
- 召回文案以弹窗形式展示；
- 提供复制按钮。

召回文案示例：

```text
最近小红书上“平价通勤包”相关内容热度明显上升，和你之前关注的女包选品方向非常接近。我们为你整理了一批近期增长较快的细分类目和内容切入角度，可以回来看看有没有适合上新的方向。
```

---

## 6. 用户注册与认证需求

系统需要支持用户注册、登录、权限识别。

注册时用户需要填写：

1. 名字；
2. 密码；
3. 偏好领域；
4. 常关注平台；
5. 可选：主要经营方向。

账号生成规则：

1. 用户填写 `display_name`；
2. 系统自动生成唯一 `account_id`；
3. `account_id` 可采用 `TL + 日期 + 随机数字`，例如：`TL202605100001`；
4. 用户登录时可以使用 `account_id` 或用户名登录，具体实现可根据工程复杂度决定。

角色：

```text
- normal_user
- admin
```

权限：

### normal_user

- 访问智能运营台；
- 访问最新爆品；
- 上传公开热点条目；
- 查看自己的对话历史；
- 编辑自己的基础偏好。

### admin

- 拥有 normal_user 的所有权限；
- 访问用户洞察；
- 访问一键召回；
- 管理所有爆品条目；
- 上传 RAG 内部文档；
- 查看用户画像；
- 生成用户召回文案。

---

## 7. 后端核心模块

后端需要提供以下核心能力：

1. 用户认证；
2. 对话管理；
3. Agent 调度；
4. 爆品内容管理；
5. 用户画像管理；
6. 记忆系统；
7. RAG 文档上传、切分、向量化、检索；
8. 一键召回文案生成；
9. admin 权限控制。

建议 API：

### Auth

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### Chat

```text
POST /api/chat/message
GET  /api/chat/history
GET  /api/chat/sessions
POST /api/chat/session
```

### Trending

```text
GET    /api/trending
POST   /api/trending
PUT    /api/trending/{id}
DELETE /api/trending/{id}
```

### Admin

```text
GET  /api/admin/users
GET  /api/admin/user-insights
POST /api/admin/rag/upload
GET  /api/admin/rag/documents
```

### Recall

```text
GET  /api/recall/candidates
POST /api/recall/generate
```

### Memory

```text
GET  /api/users/{user_id}/memory
POST /api/users/{user_id}/memory/summarize
```

---

## 8. Agent 设计

系统包含 5 个核心 Agent。

---

### 8.1 分类决策 Agent

文件建议：

```text
agents/router_agent.py
agents/prompts/router_agent.md
```

职责：

当用户进行对话后，系统首先调用分类决策 Agent。

它需要判断用户输入是否属于 TrendLogic 的业务范围。

业务范围包括：

1. 选品咨询；
2. 流量分析；
3. 带货建议；
4. 热点分析；
5. 内容运营；
6. 用户增长；
7. 电商平台策略；
8. 商品定位；
9. 用户画像相关问题；
10. 召回策略相关问题。

如果不属于业务范围，则拒绝回答与平台功能无关的闲聊，并给出简短提示：

```text
TrendLogic 主要用于电商运营、选品分析、流量趋势和用户召回相关任务。你可以向我描述你想做的商品、平台或目标用户，我会继续帮你分析。
```

输出格式必须结构化：

```json
{
  "in_scope": true,
  "intent": "product_selection",
  "confidence": 0.91,
  "next_agent": "requirement_agent",
  "reason": "用户正在询问适合售卖的商品方向"
}
```

---

### 8.2 需求分析 Agent

文件建议：

```text
agents/requirement_agent.py
agents/prompts/requirement_agent.md
```

职责：

当用户意图属于业务范围，但需求描述不完整时，需求分析 Agent 负责多轮追问并补全需求。

它需要将用户的自然语言描述转化为结构化需求画像。

结构化需求画像字段：

```json
{
  "target_platform": "小红书",
  "target_category": "美妆",
  "budget_range": "5000-10000",
  "target_audience": "18-25岁女性",
  "content_style": "种草型",
  "sales_goal": "测试新品方向",
  "risk_preference": "低风险",
  "known_constraints": ["不想压库存", "希望轻资产"],
  "missing_fields": ["价格带", "供应链能力"]
}
```

如果信息不足，不要直接进入选品咨询，需要继续追问 1-3 个关键问题。

例如：

```text
为了更准确地帮你分析，我需要先确认三个信息：你主要想在哪个平台销售？预算大概是多少？你更偏向实物商品还是内容带货？
```

---

### 8.3 选品咨询 Agent

文件建议：

```text
agents/product_consultant_agent.py
agents/prompts/product_consultant_agent.md
```

职责：

基于需求分析 Agent 输出的需求画像，调用数据库、RAG 和实时搜索接口，给用户提供电商选品、内容方向和流量机会建议。

它可以调用：

1. RAG 知识库；
2. 最新爆品数据库；
3. 用户历史偏好；
4. 外部搜索工具；
5. 平台趋势数据；
6. 商品类目数据库。

输出内容建议包括：

1. 推荐方向；
2. 适合平台；
3. 目标用户；
4. 核心卖点；
5. 内容切入角度；
6. 风险提示；
7. 起步建议；
8. 可执行下一步。

输出示例：

```text
基于你当前的需求，我建议优先考虑“便携式桌面收纳类产品”。

原因：
1. 小红书和抖音近期对“桌面改造”“学生党收纳”“租房好物”类内容关注度较高；
2. 该类产品客单价适中，适合低预算测试；
3. 内容展示性强，适合短视频和图文种草；
4. 供应链门槛较低。

你可以优先测试以下 3 个方向：
- 折叠式桌面置物架；
- 透明亚克力收纳盒；
- 带氛围灯的桌面整理套装。
```

---

### 8.4 用户画像 Agent

文件建议：

```text
agents/user_profile_agent.py
agents/prompts/user_profile_agent.md
```

职责：

系统需要记录并分析每一位用户的交互行为，形成长期画像。

用户画像 Agent 负责从用户对话、点击、上传、反馈和访问行为中提取长期偏好。

需要分析：

1. 用户经常关注的垂直领域；
2. 用户常用平台；
3. 用户偏好的内容风格；
4. 用户预算区间；
5. 用户是否偏好低风险方案；
6. 用户是否关注供应链；
7. 用户是否关注短视频带货；
8. 用户是否关注跨境电商；
9. 用户最近兴趣变化；
10. 用户不再关注的领域。

用户画像更新逻辑：

用户画像不是简单追加，而是需要动态更新。

对于新出现的兴趣：

- 如果多次出现，则提升权重；
- 如果只是一次性出现，则暂时弱记录。

对于长期未出现的兴趣：

- 不直接删除；
- 逐步降低权重；
- 在下一次总结时弱化该兴趣。

兴趣权重示例：

```json
{
  "美妆": 0.86,
  "小红书": 0.78,
  "低成本试错": 0.72,
  "数码配件": 0.31
}
```

---

### 8.5 用户召回 Agent

文件建议：

```text
agents/user_recall_agent.py
agents/prompts/user_recall_agent.md
```

职责：

用户召回 Agent 面向 admin 后台，用于生成老用户召回文案。

它需要综合：

1. 用户历史画像；
2. 用户最近一次对话；
3. 用户长期关注类目；
4. 当前最新爆品；
5. 当前热点趋势；
6. 用户访问频率；
7. 用户沉默时间。

召回优先级评分建议：

```text
recall_score = 
    用户历史活跃度 * 0.25
  + 最近热点匹配度 * 0.35
  + 用户沉默时间权重 * 0.20
  + 用户价值评分 * 0.20
```

生成召回文案时要避免太机械。

输出格式：

```json
{
  "user_id": "xxx",
  "recall_score": 0.82,
  "matched_trends": ["小红书通勤包", "平价女包", "春夏穿搭"],
  "reason": "用户曾多次关注女包和小红书种草内容，当前热点与其历史偏好高度匹配。",
  "message": "最近小红书上平价通勤包和春夏搭配相关内容热度上升，和你之前关注的女包选品方向非常接近。我们已经帮你整理了一批近期增长较快的细分类目，可以回来看看有没有适合测试的新品方向。"
}
```

---

## 9. Agent 编排流程

用户发起对话后，后端需要调用 Agent Orchestrator。

基本流程如下：

1. 接收用户输入；
2. 读取当前会话短期记忆；
3. 读取用户长期画像摘要；
4. 调用分类决策 Agent；
5. 如果不在业务范围，直接返回拒答；
6. 如果在业务范围，但需求不完整，调用需求分析 Agent；
7. 如果需求完整，调用选品咨询 Agent；
8. 选品咨询 Agent 可调用 RAG、爆品数据库、搜索工具；
9. 输出最终结果；
10. 将本轮对话写入短期记忆；
11. 判断是否需要触发长期记忆总结；
12. 必要时调用用户画像 Agent 更新长期画像。

Agent 编排输出需要支持两类消息：

1. `trace` 消息：展示给前端的 Agent 执行日志；
2. `final` 消息：展示给用户的最终对话回复。

后端返回示例：

```json
{
  "session_id": "s_123",
  "messages": [
    {
      "type": "trace",
      "agent": "分类决策Agent",
      "function": "意图识别",
      "content": "用户问题属于选品咨询场景，准备进入需求分析流程。"
    },
    {
      "type": "trace",
      "agent": "需求分析Agent",
      "function": "需求补全",
      "content": "用户尚未说明目标平台和预算，需要继续追问。"
    },
    {
      "type": "final",
      "agent": "TrendLogic",
      "content": "我可以帮你做选品分析。为了更准确地推荐方向，请先告诉我：你主要想在哪个平台销售？预算大概是多少？"
    }
  ]
}
```

---

## 10. 记忆系统设计

记忆系统分为短期记忆和长期记忆。

---

### 10.1 短期记忆

短期记忆用于维持当前对话上下文。

默认策略：

1. 保存最近 10 轮对话；
2. 或保存不超过指定 token 上限的上下文；
3. 超过上限后，较早内容进入摘要；
4. 当前会话结束后，短期记忆可用于生成长期记忆摘要。

短期记忆存储字段：

```text
- session_id
- user_id
- role
- content
- created_at
- token_count
```

---

### 10.2 长期记忆

长期记忆用于形成用户画像和长期偏好。

触发总结条件：

1. 每 10 轮对话触发一次；
2. 每一次完整业务咨询结束后触发一次；
3. 用户显式反馈“这个有用/没用”后触发一次；
4. admin 后台可手动触发总结。

长期记忆内容：

1. 用户关注领域；
2. 用户关注平台；
3. 用户预算偏好；
4. 用户风险偏好；
5. 用户内容风格偏好；
6. 用户明确不感兴趣的方向；
7. 用户最近兴趣变化；
8. 可用于召回的标签。

长期记忆更新策略：

不要每次都简单覆盖，也不要无限追加。

需要维护一个“带权重的用户兴趣图谱”。

每次总结时：

1. 新兴趣多次出现，提高权重；
2. 旧兴趣长时间未出现，降低权重；
3. 用户明确否定的兴趣，降低权重或加入 `negative_preferences`；
4. 用户频繁追问的方向，提高权重；
5. 用户反馈有用的推荐，提高相关标签权重。

推荐数据结构：

```json
{
  "user_id": "xxx",
  "summary": "用户主要关注小红书平台的低成本美妆和生活方式类选品，偏好轻资产、低库存风险的试错方案。",
  "interest_weights": {
    "小红书": 0.91,
    "美妆": 0.84,
    "低成本试错": 0.79,
    "生活方式": 0.67,
    "数码配件": 0.25
  },
  "negative_preferences": ["高库存", "高客单价奢侈品"],
  "last_updated": "2026-05-10T10:00:00"
}
```

---

## 11. RAG 模块设计

RAG 必须作为独立模块实现，不能写死在某个 Agent 中。

默认使用 LanceDB 作为向量数据库。

RAG 需要支持：

1. admin 上传文档；
2. 文档解析；
3. 文本切分；
4. Embedding 生成；
5. 向量入库；
6. 相似度检索；
7. 返回上下文片段；
8. 支持后续替换 Embedding 模型；
9. 支持后续替换 LLM。

RAG 模块接口建议：

```python
class RAGService:
    def add_document(self, file_path: str, metadata: dict) -> dict:
        pass

    def add_text(self, text: str, metadata: dict) -> dict:
        pass

    def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list:
        pass
```

文档 metadata 建议：

```json
{
  "source": "admin_upload",
  "category": "选品资料",
  "visibility": "private_rag_only",
  "uploaded_by": "admin_user_id",
  "created_at": "..."
}
```

---

## 12. MCP / Tool 模块设计

MCP 作为后续扩展工具层，先预留独立模块。

当前阶段可以先实现工具注册机制，不一定完整接入 MCP 协议。

工具包括：

1. RAG 检索工具；
2. 爆品数据库查询工具；
3. 用户画像查询工具；
4. 外部搜索工具；
5. 商品趋势分析工具；
6. 召回候选用户查询工具。

工具注册示例：

```python
TOOL_REGISTRY = {
    "rag_search": rag_search_tool,
    "query_trending_items": query_trending_items_tool,
    "query_user_profile": query_user_profile_tool,
    "generate_recall_message": generate_recall_message_tool,
}
```

---

## 13. 数据库模型建议

至少需要以下表。

### users

```text
- id
- account_id
- display_name
- password_hash
- role
- preferences
- created_at
- updated_at
```

### chat_sessions

```text
- id
- user_id
- title
- created_at
- updated_at
```

### chat_messages

```text
- id
- session_id
- user_id
- role
- content
- message_type
- agent_name
- created_at
```

### trending_items

```text
- id
- title
- category
- summary
- source
- heat_score
- tags
- visibility
- is_ai_generated
- created_by
- created_at
- updated_at
```

### uploaded_documents

```text
- id
- filename
- file_path
- category
- visibility
- uploaded_by
- vectorized
- created_at
```

### user_profiles

```text
- id
- user_id
- summary
- interest_weights
- negative_preferences
- preferred_platforms
- preferred_categories
- recall_score
- last_active_at
- updated_at
```

### memory_summaries

```text
- id
- user_id
- session_id
- summary
- extracted_preferences
- created_at
```

### recall_records

```text
- id
- user_id
- recall_score
- matched_trends
- generated_message
- created_at
- created_by
```

---

## 14. 开发顺序

请按照以下顺序开发，不要一开始就追求大而全。

---

### Phase 1：基础项目骨架

1. 检查现有项目结构；
2. 创建或整理 `frontend`、`backend`、`agents`、`rag`、`mcp` 目录；
3. 搭建 Django 后端；
4. 搭建前端基础页面；
5. 配置环境变量；
6. 添加 README 和 `.env.example`。

---

### Phase 2：用户系统

1. 实现用户注册；
2. 实现用户登录；
3. 实现 JWT 鉴权；
4. 实现 admin / normal_user 权限；
5. 前端接入登录弹窗。

---

### Phase 3：对话系统

1. 实现聊天页面；
2. 实现 chat session；
3. 实现消息存储；
4. 实现后端 `/api/chat/message`；
5. 前端展示 trace 消息和 final 消息。

---

### Phase 4：Agent 编排

1. 实现 `BaseAgent`；
2. 实现 `RouterAgent`；
3. 实现 `RequirementAgent`；
4. 实现 `ProductConsultantAgent`；
5. 实现 `Orchestrator`；
6. 打通用户输入到 Agent 输出的完整流程。

---

### Phase 5：爆品页面

1. 实现 `trending_items` 数据模型；
2. 实现最新爆品 API；
3. 实现普通用户上传公开热点；
4. 实现 admin 管理功能；
5. 实现前端最新爆品页面。

---

### Phase 6：RAG

1. 实现 LanceDB 初始化；
2. 实现 Embedding 配置；
3. 实现文档上传；
4. 实现文本切分；
5. 实现向量入库；
6. 实现 RAG 检索；
7. 将 RAG 工具接入选品咨询 Agent。

---

### Phase 7：记忆与用户画像

1. 实现短期记忆；
2. 实现长期记忆摘要；
3. 实现用户兴趣权重更新；
4. 实现用户画像 Agent；
5. 实现 admin 用户洞察页面。

---

### Phase 8：一键召回

1. 实现召回候选用户计算；
2. 实现热点与用户画像匹配；
3. 实现用户召回 Agent；
4. 实现召回文案生成；
5. 实现 admin 一键召回页面。

---

## 15. 前端 UI 风格

整体风格应简洁、现代、偏运营工作台。

建议布局：

1. 左侧 Sidebar：
   - 智能运营台
   - 最新爆品
   - 用户洞察 admin only
   - 一键召回 admin only
2. 顶部 Header：
   - 当前用户
   - 登录状态
   - 退出登录
3. 主区域：
   - 根据路由展示对应页面

聊天页面：

1. trace 消息使用灰色、小字号、缩进展示；
2. final 消息使用正常气泡；
3. 用户消息靠右；
4. AI 消息靠左；
5. 输入框固定底部。

---

## 16. 重要实现约束

1. 不要在前端写死 admin 权限，后端必须做权限校验。
2. 不要把 API Key 写入代码，必须通过 `.env` 管理。
3. 不要把 RAG 和 Agent 强耦合。
4. 不要把具体模型供应商写死。
5. 不要展示模型真实链式思考，只展示可解释执行日志。
6. 不要让分类决策 Agent 回答所有闲聊，非业务问题需要拒答。
7. 不要让普通用户访问用户洞察和一键召回接口。
8. 不要让普通用户上传 `private_rag_only` 文档。
9. 所有 JSON 字段前后端需要保持一致。
10. 所有接口需要有基本错误处理。

---

## 17. 当前优先目标：MVP

请先完成 MVP，而不是一次性实现所有复杂功能。

MVP 必须包含：

1. 用户注册/登录；
2. admin / normal_user 角色；
3. 智能运营台聊天页面；
4. Agent trace 展示；
5. 分类决策 Agent；
6. 需求分析 Agent；
7. 选品咨询 Agent 的基础版本；
8. 最新爆品页面；
9. admin 可上传爆品内容；
10. 基础短期记忆。

RAG、用户画像、一键召回可以先设计接口和目录，后续逐步实现。

---

## 18. 推荐命名

### 页面命名

| 原名称 | 建议名称 | 英文路由 |
|---|---|---|
| 默认对话 | 智能运营台 | `/chat` |
| 最新爆品 | 最新爆品 | `/trending` |
| 用户画像 | 用户洞察 | `/user-insights` |
| 一键召回 | 一键召回 | `/recall` |

### Agent 命名

| 中文名 | 代码名 |
|---|---|
| 分类决策 Agent | `RouterAgent` |
| 需求分析 Agent | `RequirementAgent` |
| 选品咨询 Agent | `ProductConsultantAgent` |
| 用户画像 Agent | `UserProfileAgent` |
| 用户召回 Agent | `RecallAgent` |

---

## 19. 请开始执行

请你现在开始工作。

第一步：

1. 检查当前项目目录结构；
2. 判断项目已有前端、后端和依赖情况；
3. 给出你准备采用的实现方案；
4. 列出第一批需要创建或修改的文件；
5. 然后开始实现 Phase 1 和 Phase 2 的基础功能。

在每次修改代码后，请说明：

- 修改了哪些文件；
- 新增了哪些能力；
- 如何运行；
- 还有哪些待完成事项。
