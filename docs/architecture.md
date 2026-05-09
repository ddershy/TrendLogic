# TrendLogic Architecture

TrendLogic 采用前后端分离结构：

- `frontend/`：React 工作台，负责登录、聊天、爆品、用户洞察和召回页面。
- `backend/`：FastAPI API，负责鉴权、数据模型、权限控制和服务编排。
- `agents/`：规则版 Multi-Agent 编排，后续可替换为 LLM、Function Calling 或 LangGraph。
- `rag/`：独立 RAG 模块，当前提供可测试的本地向量接口，后续替换为 LanceDB。
- `mcp/`：工具注册和调用层，为 MCP 协议接入预留边界。
