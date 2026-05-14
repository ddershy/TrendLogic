from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient
from mcp.client import MCPToolClient


PRODUCT_CONSULTANT_PROMPT = """
你是 TrendLogic 的电商运营咨询 Agent，负责选品、定价、内容和低风险试错建议。

你的任务不是继续追问，而是在已知信息不完整时也给出可执行建议。
你可以明确说明哪些是假设，并给出低风险试错方案。

关键要求：
- 必须优先理解 latest_user_input，不要只根据 requirement_profile 套模板。
- 如果 trend_context 里有 rag_results，请把它当作内部知识库参考资料来吸收总结，不要把召回原文整段复制给用户。
- 可以用“根据内部资料/知识库倾向”这样的表达，但不要暴露 chunk、score、metadata 等技术细节。
- 如果 task_type=pricing_strategy，或者 latest_user_input 在问“定价多少合理、原价 80%/120%、折扣、毛利、价格带”，你的回答必须以定价分析为主。
- 定价分析时不要输出普通“优先测试方向”模板；应输出价格带、倍率建议、测试分组、毛利/转化风险和下一步验证方法。
- 如果缺少成本、竞品价或目标毛利，可以用假设区间分析，不要继续追问。

输出要求：
- 你只能输出 JSON，不要输出 Markdown；
- 建议必须具体，不能只说“结合趋势分析”；
- 包含：方向判断或定价判断、建议优先级、预算/试错建议、风险提示、下一步动作；
- 如果目标用户不明确，给出 2-3 个可测试用户假设，不要把问题再抛回给用户。

JSON 格式：
{
  "process_message": "我会先判断这是选品还是定价问题，再结合上下文生成建议。",
  "assumptions": ["目标用户暂按学生党和轻度二次元用户处理"],
  "recommendations": [
    {
      "direction": "主推价按原价 90%-100%，引流款按 80%-85%，高设计感款可测 110%-120%",
      "reason": "用三个价格梯度同时验证转化率和毛利，不把所有 SKU 压在同一倍率",
      "test_budget": "先用 3-5 个 SKU 小流量测试",
      "risk_level": "中"
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
        user_input: str = "",
    ) -> ProductConsultantResult:
        tool_context = self.collect_tool_context(requirement_profile, memory_context or {}, trend_context or {}, user_input=user_input)
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
                                    "latest_user_input": user_input,
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
            fallback = self._fallback_result(requirement_profile, tool_context, user_input=user_input)
            fallback.process_message = f"{fallback.process_message} 模型响应超时或不可用，已使用本地兜底建议。"
            return fallback

        normalized = self.normalize_result(result)
        normalized.process_message = self._append_tool_summary(normalized.process_message, tool_context)
        return normalized

    def collect_tool_context(
        self,
        requirement_profile: dict[str, Any],
        memory_context: dict[str, Any],
        trend_context: dict[str, Any],
        user_input: str = "",
    ) -> dict[str, Any]:
        base_context = dict(trend_context or {})
        rag_results = self._query_rag_results(user_input, requirement_profile)
        if rag_results:
            base_context["rag_results"] = rag_results

        fallback_items = self._query_trending_items(requirement_profile)
        if fallback_items and not base_context.get("trending_items"):
            base_context["trending_items"] = fallback_items

        if not self.llm_client or not self.llm_client.is_configured or not _tool_planner_enabled():
            return base_context

        try:
            response = self.llm_client.chat_with_tools(
                [
                    {
                        "role": "system",
                        "content": (
                            "你是 TrendLogic 的工具规划器。请只在需要时调用工具收集上下文，"
                            "不要输出最终选品建议。RAG 已经由系统预检索过，不要重复调用 rag_search。"
                            "优先查询 query_trending_items；如果有 user_id，"
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
        if tool_context.get("rag_results"):
            tool_names.append("rag_search")
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
        final_message = self._compose_final_message(
            recommendations,
            assumptions,
            risk_notes,
            next_actions,
            title=str(result.get("result_title") or "").strip(),
        )
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

    def _query_rag_results(self, user_input: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
        query_parts = [
            user_input,
            str(profile.get("target_platform") or ""),
            str(profile.get("target_category") or ""),
            str(profile.get("business_goal") or ""),
            str(profile.get("task_type") or ""),
        ]
        query = " ".join(part for part in query_parts if part.strip()).strip()
        if not query:
            return []
        try:
            results = self.tool_client.call("rag_search", query=query, top_k=4, filters={})
        except Exception:
            return []
        if not isinstance(results, list):
            return []
        return [
            {
                "text": str(item.get("text") or "")[:900],
                "source": (item.get("metadata") or {}).get("filename", ""),
                "category": (item.get("metadata") or {}).get("category", ""),
                "score": item.get("score"),
            }
            for item in results[:4]
            if isinstance(item, dict) and item.get("text")
        ]

    def _compose_final_message(
        self,
        recommendations: list[ProductRecommendation],
        assumptions: list[str],
        risk_notes: list[str],
        next_actions: list[str],
        title: str = "",
    ) -> str:
        lines = [title or "可以，我先按现有信息给你一版可执行建议。"]
        if assumptions:
            lines.append("\n### 判断前提")
            lines.extend(f"- {item}" for item in assumptions)
        if recommendations:
            lines.append("\n### 建议方案")
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

    def _fallback_result(
        self,
        requirement_profile: dict[str, Any],
        tool_context: dict[str, Any],
        user_input: str = "",
    ) -> ProductConsultantResult:
        platform = str(requirement_profile.get("target_platform") or "内容平台")
        category = str(requirement_profile.get("target_category") or "当前类目")
        budget = requirement_profile.get("budget_range")
        budget_text = f"{budget:g} 元" if isinstance(budget, int | float) else "小预算"
        rag_results = tool_context.get("rag_results") or []
        source_hint = ""
        if rag_results:
            sources = _unique([str(item.get("source") or "") for item in rag_results if isinstance(item, dict)])
            if sources:
                source_hint = f"参考资料：{', '.join(sources[:3])}。"
        result = {
            "process_message": "我会基于已识别需求、RAG 资料和爆品库生成快速兜底建议。",
            "assumptions": [f"平台暂按{platform}处理", f"类目暂按{category}处理", source_hint or "先按低风险测品场景处理"],
            "recommendations": [
                {
                    "direction": f"先用{budget_text}测试 3-5 个{category} SKU",
                    "reason": "用少量 SKU 同时验证点击、收藏、加购和成交，避免把预算压在单个商品上",
                    "test_budget": "每个 SKU 先做 2-3 条内容，保留数据最好的 1-2 个方向放大",
                    "risk_level": "中低",
                },
                {
                    "direction": f"内容上优先匹配{platform}的高转化场景词",
                    "reason": "先用明确痛点、可视化效果和真实测评降低用户决策成本",
                    "test_budget": "首轮以自然流量和小额投放验证，不建议重库存",
                    "risk_level": "中",
                },
            ],
            "risk_notes": ["外部模型不可用时，本地建议更偏保守，需要结合实际供应链和毛利再确认。", "先看点击率、互动率、加购率，再决定是否补货。"],
            "next_actions": ["整理 5 个候选 SKU", "每个 SKU 写 2 个内容角度", "48-72 小时后按数据淘汰低效方向"],
            "memory_candidates": [
                {
                    "candidate_type": "business_need",
                    "content": f"用户希望在{platform}测试{category}方向",
                    "tags": [platform, category],
                }
            ],
        }
        return self.normalize_result(result)


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


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _tool_planner_enabled() -> bool:
    return os.getenv("PRODUCT_CONSULTANT_TOOL_PLANNER", "false").lower() in {"1", "true", "yes", "on"}
