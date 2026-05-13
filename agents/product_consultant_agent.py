from __future__ import annotations

import json
from typing import Any

from .llm_client import LLMClient


PRODUCT_CONSULTANT_PROMPT = """
你是 TrendLogic 的选品咨询 Agent。

你的任务不是继续追问，而是在已知信息不完整时也给出可执行建议。
你可以明确说明哪些是假设，并给出低风险试错方案。

输出要求：
- 用中文直接给用户建议；
- 不要输出 JSON；
- 结构清晰，包含：方向判断、建议优先级、预算/试错建议、下一步动作；
- 如果目标用户不明确，给出 2-3 个可测试用户假设，不要把问题再抛回给用户。
""".strip()


class ProductConsultantAgent:
    name = "选品咨询Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        try:
            self.llm_client = llm_client or LLMClient()
        except Exception:
            self.llm_client = None

    def run(self, requirement_profile: dict[str, Any], memory_context: dict[str, Any] | None = None) -> str:
        if self.llm_client and self.llm_client.is_configured:
            try:
                return self.llm_client.chat(
                    [
                        {"role": "system", "content": PRODUCT_CONSULTANT_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "requirement_profile": requirement_profile,
                                    "memory_context": memory_context or {},
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ]
                )
            except Exception:
                pass
        return self._fallback(requirement_profile, memory_context or {})

    def _fallback(self, profile: dict[str, Any], memory_context: dict[str, Any]) -> str:
        platform = profile.get("target_platform") or "你主要经营的平台"
        category = profile.get("target_category") or "当前类目"
        budget = profile.get("budget_range") or "小预算"
        audience = profile.get("target_audience") or "待验证用户群体"
        preferences = memory_context.get("preferences") or []
        preference_text = f"我会参考你之前偏好的 {', '.join(preferences[:3])}。" if preferences else ""

        return (
            f"可以，我先按现有信息给你一个可执行判断。{preference_text}\n\n"
            f"方向判断：{category} 可以先在 {platform} 做小批量内容测试，预算按 {budget} 控制，不建议一开始重库存。\n\n"
            "优先测试 3 个方向：\n"
            f"1. 面向“{audience}”的高展示性单品，适合先看点击、收藏和评论；\n"
            "2. 低客单价组合装，用来提高转化率和降低用户决策成本；\n"
            "3. 有内容话题的细分款，比如开箱、对比、场景化使用更容易讲清楚的商品。\n\n"
            "预算建议：先把 60% 用在 3-5 个商品的小样和素材测试，30% 留给表现最好的方向补内容，10% 做备用。\n\n"
            "下一步动作：先选 3 个候选商品，各发 2 条内容，观察收藏率、评论里的购买意图和私信咨询，再决定是否进货。"
        )
