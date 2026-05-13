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
- 你必须综合“当前用户输入”和“用户记忆上下文/当前会话历史”，不要只看最后一句话。
- 对选品/开店/运营建议类问题，核心字段是 target_platform、target_category、budget_range、target_audience。
- 如果你判断用户已经在请求专业建议、判断、推荐或方案，不要继续追问，应基于现有信息返回 should_enter_consulting=true。
- 如果用户没有明确咨询意图，核心字段都已经从当前输入或会话历史中明确识别，才返回 is_complete=true，进入下一流程。
- 如果只缺少 content_style、risk_preference、known_constraints 这类优化字段，不要反复追问，可以先进入下一流程。
- 如果信息不足，missing_fields 只列最关键的 1-2 项，并提出一个自然追问。
- process_message 要精简，说明已经识别到哪些信息，以及为什么继续或追问。


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
  "should_enter_consulting": false,
  "consulting_reason": "用户仍在补充基础条件，暂时不是请求完整建议。",
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
    should_enter_consulting: bool = False
    consulting_reason: str = ""


class RequirementAgent:
    name = "需求分析Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def normalize_result(
        self,
        result: dict[str, Any],
        memory_context: dict[str, Any] | None = None,
    ) -> RequirementResult:
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
        should_enter_consulting = bool(result.get("should_enter_consulting", False))
        consulting_reason = str(result.get("consulting_reason") or "").strip()
        core_fields = ["target_platform", "target_category", "budget_range", "target_audience"]
        missing_core_fields = [field for field in core_fields if not normalized_profile.get(field)]
        enough_to_advise = bool(normalized_profile.get("target_category")) and bool(
            normalized_profile.get("target_platform")
            or normalized_profile.get("budget_range")
            or normalized_profile.get("target_audience")
            or (memory_context or {}).get("recent_user_transcript")
        )

        if should_enter_consulting and enough_to_advise:
            is_complete = True
            missing_fields = []
        elif missing_core_fields:
            is_complete = False
            missing_fields = _unique([*missing_core_fields, *missing_fields])[:2]
        else:
            is_complete = True
            missing_fields = [
                field
                for field in missing_fields
                if field in set(core_fields)
            ][:1]

        follow_up_question = str(result.get("follow_up_question") or "").strip()
        if not is_complete and not follow_up_question:
            follow_up_question = self._build_follow_up_question(missing_fields)
        if is_complete:
            follow_up_question = ""

        process_message = str(result.get("process_message") or "").strip()
        if not process_message:
            process_message = "我正在整理你的需求信息，先确认平台、类目、预算和目标用户是否清晰。"
        if is_complete and self._looks_like_follow_up(process_message):
            process_message = consulting_reason or "用户已经开始请求具体建议，我会基于现有信息进入选品咨询，不再继续追问。"
        if not is_complete and not self._looks_like_follow_up(process_message):
            process_message = f"我已经整理出部分需求，但还缺少{self._field_label(missing_fields[0]) if missing_fields else '一个关键信息'}，需要先补充后再进入下一步。"

        return RequirementResult(
            is_complete=is_complete,
            requirement_profile=normalized_profile,
            missing_fields=missing_fields,
            follow_up_question=follow_up_question,
            process_message=process_message,
            should_enter_consulting=should_enter_consulting,
            consulting_reason=consulting_reason,
        )

    def run(self, user_input: str, memory_context: dict[str, Any] | None = None) -> RequirementResult:
        memory_text = ""
        if memory_context:
            memory_text = (
                "以下是用户记忆上下文和当前会话历史。你必须把它和最新用户输入合并理解；"
                "不要因为最新一句话很短就忽略之前已经提供的信息，也不要直接暴露这些上下文给用户：\n"
                f"{json.dumps(memory_context, ensure_ascii=False)}"
            )
        messages = [
            {"role": "system", "content": REQUIREMENT_PROMPT},
            *([{"role": "system", "content": memory_text}] if memory_text else []),
            {"role": "user", "content": user_input},
        ]
        result = self.llm_client.chat_json(messages)
        return self.normalize_result(result, memory_context=memory_context)


    @staticmethod
    def _ensure_list(value: object) -> list[str]:
        if isinstance(value, list): # 列表返回成字符串的列表，过滤掉空字符串和只包含空格的字符串
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip(): # 字符串返回成单元素列表，前提是字符串不为空或不全是空格
            return [value.strip()]
        return []

    @classmethod
    def _build_follow_up_question(cls, missing_fields: list[str]) -> str:
        if not missing_fields:
            return "为了更准确地分析，请再补充一个关键信息。"
        labels = [cls._field_label(field) for field in missing_fields[:2]]
        return f"为了继续做选品分析，请先补充：{'、'.join(labels)}。"

    @staticmethod
    def _field_label(field: str) -> str:
        labels = {
            "target_platform": "目标平台",
            "target_category": "商品类目",
            "budget_range": "预算范围",
            "target_audience": "目标用户群体",
            "sales_goal": "销售目标",
            "content_style": "内容形式",
            "risk_preference": "风险偏好",
            "known_constraints": "限制条件",
        }
        return labels.get(field, field)

    @staticmethod
    def _looks_like_follow_up(text: str) -> bool:
        return any(word in text for word in ["缺少", "还缺", "还需要", "需要明确", "补充", "不明确"])


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
