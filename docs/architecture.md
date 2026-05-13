# TrendLogic Architecture

TrendLogic 采用前后端分离结构：

- `frontend/`：Vue 工作台，负责登录、聊天、爆品、用户洞察和召回页面。
- `backend/`：Django JSON API，负责鉴权、数据模型、权限控制和服务编排。
- `agents/`：LangGraph Multi-Agent 编排，部分 Agent 已接入 LLM 和 Function Calling。
- `rag/`：独立 RAG 模块，当前提供可测试的本地向量接口，后续替换为 LanceDB。
- `mcp/`：工具注册和调用层，提供 OpenAI tools schema 与本地工具执行，后续可替换为完整 MCP server。

更多细节见 `docs/function_calling_mcp.md`。
