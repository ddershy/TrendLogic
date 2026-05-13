from __future__ import annotations

from agents.tools.database_tool import (
    query_recent_chat_sessions_tool,
    query_recall_records_tool,
    query_user_memory_tool,
    query_user_profile_tool,
    query_user_workspace_tool,
)
from agents.tools.rag_tool import rag_search_tool
from agents.tools.search_tool import search_tool
from agents.tools.trend_tool import query_trending_categories_tool, query_trending_items_tool, query_trending_stats_tool

from .registry import TOOL_REGISTRY, register_tool


def register_builtin_tools() -> None:
    if TOOL_REGISTRY:
        return

    register_tool(
        "query_trending_items",
        query_trending_items_tool,
        description="查询 TrendLogic 最新爆品库，可按类目、标签和关键词筛选。",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "爆品类目，可为空。"},
                "keyword": {"type": "string", "description": "标题或摘要关键词，可为空。"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要匹配的标签列表，可为空。",
                },
                "limit": {"type": "integer", "description": "最多返回条数，默认 5。"},
            },
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_user_profile",
        query_user_profile_tool,
        description="按 user_id 查询用户画像摘要、偏好类目、平台和兴趣权重。",
        parameters={
            "type": "object",
            "properties": {"user_id": {"type": "string", "description": "用户 ID。"}},
            "required": ["user_id"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_user_memory",
        query_user_memory_tool,
        description="按 user_id 查询用户长期记忆、偏好、经营需求和召回信号。",
        parameters={
            "type": "object",
            "properties": {"user_id": {"type": "string", "description": "用户 ID。"}},
            "required": ["user_id"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_recent_chat_sessions",
        query_recent_chat_sessions_tool,
        description="按 user_id 查询用户最近几次完整会话摘要和用户输入片段。",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID。"},
                "limit": {"type": "integer", "description": "返回会话数量，默认 5。"},
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_recall_records",
        query_recall_records_tool,
        description="按 user_id 查询用户近期召回记录。",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID。"},
                "limit": {"type": "integer", "description": "返回记录数量，默认 5。"},
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_user_workspace",
        query_user_workspace_tool,
        description="按 user_id 一次性查询用户画像、记忆、近期会话和召回记录。",
        parameters={
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "用户 ID。"},
                "session_limit": {"type": "integer", "description": "返回最近会话数量，默认 5。"},
            },
            "required": ["user_id"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_trending_categories",
        query_trending_categories_tool,
        description="查询最新爆品库的可用分类。",
        parameters={
            "type": "object",
            "properties": {"active_only": {"type": "boolean", "description": "是否只返回启用分类，默认 true。"}},
            "additionalProperties": False,
        },
    )
    register_tool(
        "query_trending_stats",
        query_trending_stats_tool,
        description="查询公开爆品库的类目数量和热门标签统计。",
        parameters={
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "热门标签返回数量，默认 10。"}},
            "additionalProperties": False,
        },
    )
    register_tool(
        "rag_search",
        rag_search_tool,
        description="检索内部 RAG 知识库中的运营资料。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索问题。"},
                "top_k": {"type": "integer", "description": "返回条数，默认 5。"},
                "filters": {"type": "object", "description": "可选过滤条件。"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    register_tool(
        "search_web",
        search_tool,
        description="通过 SerpApi 执行 Google 搜索，返回关键内容。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词。"},
                "limit": {"type": "integer", "description": "返回数量，默认 3。"},
                "hl": {"type": "string", "description": "搜索语言，默认 zh-cn。"},
                "gl": {"type": "string", "description": "搜索国家/地区，默认 cn。"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )

