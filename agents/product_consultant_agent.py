from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient
from mcp.client import MCPToolClient


PRODUCT_CONSULTANT_PROMPT = """
你是 TrendLogic 的选品咨询 Agent。

你的任务不是继续追问，而是在已知信息不完整时也给出可执行建议。
你可以明确说明哪些是假设，并给出低风险试错方案。

输出要求：
- 你只能输出 JSON，不要输出 Markdown；
- 建议必须具体，不能只说“结合趋势分析”；
- 包含：方向判断、建议优先级、预算/试错建议、风险提示、下一步动作；
- 如果目标用户不明确，给出 2-3 个可测试用户假设，不要把问题再抛回给用户。

JSON 格式：
{
  "process_message": "我会基于平台、预算、类目和用户记忆生成低风险选品方案。",
  "assumptions": ["目标用户暂按学生党和轻度二次元用户处理"],
  "recommendations": [
    {
      "direction": "亚克力挂件/吧唧小套装",
      "reason": "展示性强，适合小红书图文和开箱内容",
      "test_budget": "1000-1500",
      "risk_level": "低"
    }
  ],
  "risk_notes": ["不要一开始压太多库存"],
  "next_actions": ["先选 3 个 SKU 做内容测试"],
  "memory_candidates": [
    {
      "candidate_type": "business_need",
      "content": "用户希望用 5000 元预算测试小红书二次元周边选品",
      "tags": ["小红书", "二次元周边"]
    }
  ]
}
""".strip()


@dataclass
class ProductRecommendation:
    direction: str
    reason: str
    test_budget: str = ""
    risk_level: str = ""


@dataclass
class ProductConsultantResult:
    final_message: str
    process_message: str
    recommendations: list[ProductRecommendation] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    memory_candidates: list[dict[str, Any]] = field(default_factory=list)


class ProductConsultantAgent:
    name = "选品咨询Agent"

    def __init__(self, llm_client: LLMClient | None = None, tool_client: MCPToolClient | None = None) -> None:
        self.llm_init_error = ""
        try:
            self.llm_client = llm_client or LLMClient()
        except Exception as exc:
            self.llm_client = None
            self.llm_init_error = str(exc)
        self.tool_client = tool_client or MCPToolClient()

    def run(
        self,
        requirement_profile: dict[str, Any],
        memory_context: dict[str, Any] | None = None,
        trend_context: dict[str, Any] | None = None,
    ) -> ProductConsultantResult:
        tool_context = self.collect_tool_context(requirement_profile, memory_context or {}, trend_context or {})
        if not self.llm_client:
            raise RuntimeError(f"ProductConsultantAgent 初始化 LLMClient 失败：{self.llm_init_error or 'unknown error'}")
        if not self.llm_client.is_configured:
            raise RuntimeError("ProductConsultantAgent 未配置 LLM。请检查 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL。")

        try:
            result = self.llm_client.chat_json(
                [
                    {"role": "system", "content": PRODUCT_CONSULTANT_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "requirement_profile": requirement_profile,
                                "memory_context": memory_context or {},
                                "trend_context": tool_context,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ]
            )
        except Exception as exc:
            raise RuntimeError(f"ProductConsultantAgent 调用 LLM 或解析 JSON 失败：{exc}") from exc

        normalized = self.normalize_result(result)
        normalized.process_message = self._append_tool_summary(normalized.process_message, tool_context)
        return normalized

    def collect_tool_context(
        self,
        requirement_profile: dict[str, Any],
        memory_context: dict[str, Any],
        trend_context: dict[str, Any],
    ) -> dict[str, Any]:
        base_context = dict(trend_context or {})
        fallback_items = self._query_trending_items(requirement_profile)
        if fallback_items and not base_context.get("trending_items"):
            base_context["trending_items"] = fallback_items

        if not self.llm_client or not self.llm_client.is_configured:
            return base_context

        try:
            response = self.llm_client.chat_with_tools(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是 TrendLogic 的工具规划器。请只在需要时调用工具收集上下文，"
                            "不要输出最终选品建议。优先查询 query_trending_items；如果有 user_id，"
                            "可以查询 query_user_workspace、query_recent_chat_sessions 和 query_recall_records。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "requirement_profile": requirement_profile,
                                "memory_context": memory_context,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                tools=self.tool_client.openai_tools(
                    [
                        "query_trending_items",
                        "query_trending_categories",
                        "query_trending_stats",
                        "query_user_workspace",
                        "query_user_profile",
                        "query_user_memory",
                        "query_recent_chat_sessions",
                        "query_recall_records",
                        "rag_search",
                        "search_web",
                    ]
                ),
                tool_executor=lambda name, arguments: self.tool_client.call(name, **arguments),
                max_rounds=2,
            )
        except Exception:
            return base_context

        tool_results = response.get("tool_results", [])
        base_context["tool_results"] = tool_results
        trending_items = []
        for item in tool_results:
            if item.get("name") == "query_trending_items" and isinstance(item.get("result"), list):
                trending_items.extend(item["result"])
        if trending_items:
            base_context["trending_items"] = trending_items[:8]
        return base_context

    def _append_tool_summary(self, process_message: str, tool_context: dict[str, Any]) -> str:
        tool_results = tool_context.get("tool_results") or []
        tool_names = []
        for item in tool_results:
            name = item.get("name") if isinstance(item, dict) else ""
            if name and name not in tool_names:
                tool_names.append(name)
        if not tool_names and tool_context.get("trending_items"):
            tool_names.append("query_trending_items")
        if not tool_names:
            return process_message
        return f"{process_message} 已调用工具：{', '.join(tool_names)}。"

    def normalize_result(self, result: dict[str, Any]) -> ProductConsultantResult:
        recommendations = []
        for item in _ensure_list_of_dict(result.get("recommendations")):
            recommendations.append(
                ProductRecommendation(
                    direction=str(item.get("direction") or "").strip(),
                    reason=str(item.get("reason") or "").strip(),
                    test_budget=str(item.get("test_budget") or "").strip(),
                    risk_level=str(item.get("risk_level") or "").strip(),
                )
            )
        assumptions = _ensure_list(result.get("assumptions"))
        risk_notes = _ensure_list(result.get("risk_notes"))
        next_actions = _ensure_list(result.get("next_actions"))
        memory_candidates = _ensure_list_of_dict(result.get("memory_candidates"))
        process_message = str(result.get("process_message") or "我会基于现有需求生成选品建议。").strip()
        final_message = self._compose_final_message(recommendations, assumptions, risk_notes, next_actions)
        return ProductConsultantResult(
            final_message=final_message,
            process_message=process_message,
            recommendations=recommendations,
            assumptions=assumptions,
            risk_notes=risk_notes,
            next_actions=next_actions,
            memory_candidates=memory_candidates,
        )

    def _query_trending_items(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return self.tool_client.call(
                "query_trending_items",
                category=str(profile.get("target_category") or ""),
                keyword="",
                tags=[],
                limit=5,
            )
        except Exception:
            return []

    def _compose_final_message(
        self,
        recommendations: list[ProductRecommendation],
        assumptions: list[str],
        risk_notes: list[str],
        next_actions: list[str],
    ) -> str:
        lines = ["可以，我先按现有信息给你一版可执行的选品建议。"]
        if assumptions:
            lines.append("\n### 判断前提")
            lines.extend(f"- {item}" for item in assumptions)
        if recommendations:
            lines.append("\n### 优先测试方向")
            for index, item in enumerate(recommendations, start=1):
                detail = f"{index}. **{item.direction}**：{item.reason}"
                if item.test_budget:
                    detail += f" 预算：{item.test_budget}。"
                if item.risk_level:
                    detail += f" 风险：{item.risk_level}。"
                lines.append(detail)
        if risk_notes:
            lines.append("\n### 风险提醒")
            lines.extend(f"- {item}" for item in risk_notes)
        if next_actions:
            lines.append("\n### 下一步动作")
            lines.extend(f"{index}. {item}" for index, item in enumerate(next_actions, start=1))
        return "\n".join(lines)


def _ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _ensure_list_of_dict(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []
