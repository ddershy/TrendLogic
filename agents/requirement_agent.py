"""
RequirementAgent 是 TrendLogic 的需求分析 Agent。

负责：
1. 从用户输入中提取结构化需求；
2. 判断信息是否足够进入后续选品/运营建议；
3. 如果信息不足，生成一个自然的追问问题。
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any
from .llm_client import LLMClient


REQUIREMENT_PROMPT = """
你是 TrendLogic 的需求分析 Agent。

你的任务是阅读用户输入，把模糊的电商运营需求整理成结构化需求，并判断信息是否足够进入后续分析。

你需要重点提取：
- target_platform：目标平台，例如 小红书、抖音、淘宝、TikTok、Amazon
- target_category：目标类目，例如 美妆、女包、收纳、数码、二次元、母婴
- budget_range：预算区间
- target_audience：目标用户
- content_style：内容风格，例如 种草、短视频、直播、图文
- sales_goal：销售目标，例如 测试新品、低成本副业、提高复购
- risk_preference：风险偏好，例如 低风险、轻库存、可接受囤货
- known_constraints：用户已经说明的限制条件

判断规则：
由你来判断目前的消息是否可以推断出用户的多数目标，则返回is_complete = true。
如果信息不足，is_complete=false，并在 missing_fields 中列出缺失字段。
由你来补全follow_up_question和process_message，要求内容自然且具有引导性，能够让用户清晰地理解需要补充哪些信息，以及为什么需要这些信息,但为了减少token消耗，精简输出。


你只能输出 JSON，不要输出 Markdown，不要解释。

JSON 格式：
{
  "is_complete": false,
  "requirement_profile": {
    "target_platform": "小红书",
    "target_category": "二次元周边",
    "budget_range": 5000.00,
    "target_audience": "儿童",
    "content_style": "种草",
    "sales_goal": "开店选品",
    "risk_preference": null,
    "known_constraints": []
  },
  "missing_fields": ["target_platform", "budget_range","..."],
  "follow_up_question": "为了更准确地分析，请先告诉我：……",
  "process_message": "我开始整理你的需求，目前已经识别到你关注{target_category}，但还缺少……。"
}
""".strip()


@dataclass
class RequirementResult:
    is_complete: bool
    requirement_profile: dict[str, Any]
    missing_fields: list[str]
    follow_up_question: str
    process_message: str


class RequirementAgent:
    name = "需求分析Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def normalize_result(self, result: dict[str, Any]) -> RequirementResult:
        profile = result.get("requirement_profile")
        if not isinstance(profile, dict):
            profile = {}

        normalized_profile = {
            "target_platform": profile.get("target_platform"),
            "target_category": profile.get("target_category"),
            "budget_range": profile.get("budget_range"),
            "target_audience": profile.get("target_audience"),
            "content_style": profile.get("content_style"),
            "sales_goal": profile.get("sales_goal"),
            "risk_preference": profile.get("risk_preference"),
            "known_constraints": self._ensure_list(profile.get("known_constraints")),
        }

        missing_fields = self._ensure_list(result.get("missing_fields"))
        is_complete = bool(result.get("is_complete", False))
        # if len([value for key, value in normalized_profile.items() if key in {"target_platform", "target_category", "budget_range"} and value]) >= 2:
        #     is_complete = True

        follow_up_question = str(result.get("follow_up_question") or "").strip()
        # if not is_complete and not follow_up_question:
        #     follow_up_question = "为了更准确地分析，请先告诉我：你主要想在哪个平台销售？预算大概是多少？更关注什么类目？"

        process_message = str(result.get("process_message") or "").strip()
        if not process_message:
            process_message = "我正在整理你的需求信息，先确认平台、类目、预算和目标用户是否清晰。"

        return RequirementResult(
            is_complete=is_complete,
            requirement_profile=normalized_profile,
            missing_fields=missing_fields,
            follow_up_question=follow_up_question,
            process_message=process_message,
        )

    def run(self, user_input: str, memory_context: dict[str, Any] | None = None) -> RequirementResult:
        memory_text = ""
        if memory_context:
            memory_text = (
                "以下是用户记忆上下文，只能作为理解用户偏好和当前会话背景的参考，不要直接暴露给用户：\n"
                f"{json.dumps(memory_context, ensure_ascii=False)}"
            )
        messages = [
            {"role": "system", "content": REQUIREMENT_PROMPT},
            *([{"role": "system", "content": memory_text}] if memory_text else []),
            {"role": "user", "content": user_input},
        ]
        result = self.llm_client.chat_json(messages)
        return self.normalize_result(result)


    @staticmethod
    def _ensure_list(value: object) -> list[str]:
        if isinstance(value, list): # 列表返回成字符串的列表，过滤掉空字符串和只包含空格的字符串
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip(): # 字符串返回成单元素列表，前提是字符串不为空或不全是空格
            return [value.strip()]
        return []
