# Function Calling 与 MCP 工具层

当前实现采用“本地 MCP 风格工具注册层 + OpenAI-compatible Function Calling”的方式。

## 调用链路

1. `mcp.bootstrap.register_builtin_tools()` 注册内置工具。
2. `mcp.registry` 保存工具函数、说明和 JSON Schema。
3. `MCPToolClient.openai_tools()` 把工具定义转换为 OpenAI tools 格式。
4. `LLMClient.chat_with_tools()` 执行工具调用循环：
   - 模型返回 tool_calls；
   - 本地 `MCPToolClient.call()` 执行工具；
   - 工具结果以 `tool` 消息返回给模型；
   - 模型继续生成结果。
5. `ProductConsultantAgent` 使用工具上下文辅助生成选品建议。

## 已注册工具

- `query_trending_items`：查询最新爆品库。
- `query_trending_categories`：查询爆品库分类。
- `query_trending_stats`：查询爆品库类目和标签统计。
- `query_user_profile`：查询用户画像。
- `query_user_memory`：查询用户记忆档案。
- `query_recent_chat_sessions`：查询用户近期会话摘要。
- `query_recall_records`：查询用户历史召回记录。
- `query_user_workspace`：一次性查询用户画像、记忆、近期会话和召回记录。
- `rag_search`：检索内部 RAG 资料。
- `search_web`：外部搜索占位工具。

## 设计边界

这里的 `mcp/` 还不是完整 MCP server 协议实现，而是先把工具描述、注册和调用边界抽出来。后续如果接真实 MCP server，只需要替换 `MCPToolClient.call()` 的执行方式，Agent 侧不用大改。
