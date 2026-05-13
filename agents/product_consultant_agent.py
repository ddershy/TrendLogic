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
        try:
            self.llm_client = llm_client or LLMClient()
        except Exception:
            self.llm_client = None
        self.tool_client = tool_client or MCPToolClient()

    def run(
        self,
        requirement_profile: dict[str, Any],
        memory_context: dict[str, Any] | None = None,
        trend_context: dict[str, Any] | None = None,
    ) -> ProductConsultantResult:
        tool_context = self.collect_tool_context(requirement_profile, memory_context or {}, trend_context or {})
        if self.llm_client and self.llm_client.is_configured:
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
                return self.normalize_result(result)
            except Exception:
                pass
        return self._fallback(requirement_profile, memory_context or {}, tool_context)

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
                            "可以查询 query_user_profile 和 query_user_memory。"
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
                tools=self.tool_client.openai_tools(["query_trending_items", "query_user_profile", "query_user_memory", "rag_search"]),
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

    def _fallback(
        self,
        profile: dict[str, Any],
        memory_context: dict[str, Any],
        trend_context: dict[str, Any] | None = None,
    ) -> ProductConsultantResult:
        platform = profile.get("target_platform") or "你主要经营的平台"
        category = profile.get("target_category") or "当前类目"
        budget = profile.get("budget_range") or "小预算"
        audience = profile.get("target_audience") or "待验证用户群体"
        preferences = memory_context.get("preferences") or []
        trending_items = (trend_context or {}).get("trending_items") or []
        assumptions = []
        if not profile.get("target_audience"):
            assumptions = [f"目标用户先按“{audience}”处理，后续可以根据内容数据再细分"]
        if preferences:
            assumptions.append(f"参考用户历史偏好：{', '.join(str(item) for item in preferences[:3])}")
        if trending_items:
            assumptions.append(f"已参考爆品库：{', '.join(str(item.get('title')) for item in trending_items[:3] if isinstance(item, dict))}")
        recommendations = [
            ProductRecommendation(
                direction=f"{category} 的高展示性单品",
                reason=f"适合在 {platform} 做图文、短视频或开箱内容，先看收藏和评论意向。",
                test_budget="总预算的 30%-40%",
                risk_level="低",
            ),
            ProductRecommendation(
                direction="低客单价组合装",
                reason="能降低用户决策成本，也方便做限量、套装和场景化种草。",
                test_budget="总预算的 20%-30%",
                risk_level="中低",
            ),
            ProductRecommendation(
                direction="带话题属性的细分款",
                reason="优先选择有梗、有场景、有对比点的 SKU，内容更容易被用户记住。",
                test_budget="总预算的 20%",
                risk_level="中",
            ),
        ]
        risk_notes = [
            "不要一开始重库存，先用少量 SKU 验证内容数据。",
            "如果连续 3-5 条内容没有收藏和评论意向，就及时换方向。",
        ]
        next_actions = [
            "先选 3 个候选商品，每个商品准备 2 条内容素材。",
            "记录点击、收藏、评论购买意向和私信咨询。",
            f"预算按 {budget} 控制，先把钱花在样品、素材和小批量测试上。",
        ]
        memory_candidates = [
            {
                "candidate_type": "business_need",
                "content": f"用户希望用 {budget} 预算在 {platform} 测试 {category} 选品。",
                "source_agent": "product_consultant_agent",
                "confidence": 0.72,
                "tags": [str(item) for item in [platform, category] if item],
            }
        ]
        return ProductConsultantResult(
            final_message=self._compose_final_message(recommendations, assumptions, risk_notes, next_actions),
            process_message="我会基于现有需求和用户记忆，直接给出低风险选品测试方案。",
            recommendations=recommendations,
            assumptions=assumptions,
            risk_notes=risk_notes,
            next_actions=next_actions,
            memory_candidates=memory_candidates,
        )

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
