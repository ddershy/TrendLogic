"""
RequirementAgent 是 TrendLogic 的需求分析 Agent。

负责：
1. 从用户输入中提取结构化需求；
2. 判断信息是否足够进入后续选品/运营建议；
3. 如果信息不足，生成一个自然的追问问题。
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Any
from .llm_client import LLMClient


REQUIREMENT_PROMPT = """
你是 TrendLogic 的需求分析 Agent。

你的任务是阅读用户输入，把模糊的电商运营需求整理成结构化需求，并判断信息是否足够进入后续分析。

你需要重点提取：
- task_type：用户当前任务类型，例如 product_selection / pricing_strategy / traffic_analysis / content_advice / platform_strategy
- target_platform：目标平台，例如 小红书、抖音、淘宝、TikTok、Amazon
- target_category：目标类目，例如 美妆、女包、收纳、数码、二次元、母婴
- budget_range：预算区间
- target_audience：目标用户
- content_style：内容风格，例如 种草、短视频、直播、图文
- sales_goal：销售目标，例如 测试新品、低成本副业、提高复购
- risk_preference：风险偏好，例如 低风险、轻库存、可接受囤货
- pricing_question：如果用户在问定价、利润、倍率、折扣、原价百分比，请提取成一句话；否则为 null
- price_reference：如果用户提到“原价的 80%/120%/成本/毛利”等价格锚点，请结构化记录；否则为 null
- known_constraints：用户已经说明的限制条件

判断规则：
- 你必须综合“当前用户输入”和“用户记忆上下文/当前会话历史”，不要只看最后一句话。
- 对选品/开店/运营建议类问题，核心字段是 target_platform、target_category、budget_range、target_audience。
- 如果用户主要在问“定价多少合理、原价百分比、折扣、利润、毛利、价格带”，task_type 必须设为 pricing_strategy，并且不要把它改写成普通选品问题。
- 如果用户说“查已有资料、查知识库、参考文档、根据资料”等，并且已经给出商品/类目或具体问题，应优先进入后续咨询，让咨询 Agent 先检索 RAG，不要先追问平台和预算。
- 对 pricing_strategy：只要用户已经给出商品/类目或明确的 pricing_question，就可以先进入咨询；缺少平台、预算、目标用户时，应让后续 Agent 基于知识库和合理假设回答，而不是在本节点反复追问。
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
    "task_type": "pricing_strategy",
    "target_platform": "小红书",
    "target_category": "二次元周边",
    "budget_range": 5000.00,
    "target_audience": "儿童",
    "content_style": "种草",
    "sales_goal": "开店选品",
    "risk_preference": null,
    "pricing_question": "用户想判断单品定价按原价 80% 还是 120% 更合理",
    "price_reference": {
      "base_price": "原价",
      "ratio_options": ["80%", "120%"]
    },
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
            "task_type": profile.get("task_type"),
            "target_platform": profile.get("target_platform"),
            "target_category": profile.get("target_category"),
            "budget_range": profile.get("budget_range"),
            "target_audience": profile.get("target_audience"),
            "content_style": profile.get("content_style"),
            "sales_goal": profile.get("sales_goal"),
            "risk_preference": profile.get("risk_preference"),
            "pricing_question": profile.get("pricing_question"),
            "price_reference": profile.get("price_reference"),
            "known_constraints": self._ensure_list(profile.get("known_constraints")),
        }

        missing_fields = self._ensure_list(result.get("missing_fields"))
        is_complete = bool(result.get("is_complete", False))
        should_enter_consulting = bool(result.get("should_enter_consulting", False))
        consulting_reason = str(result.get("consulting_reason") or "").strip()
        core_fields = ["target_platform", "target_category", "budget_range", "target_audience"]
        missing_core_fields = [field for field in core_fields if not normalized_profile.get(field)]
        is_pricing_task = normalized_profile.get("task_type") == "pricing_strategy" or bool(normalized_profile.get("pricing_question"))
        pricing_ready = is_pricing_task and bool(normalized_profile.get("target_category") or normalized_profile.get("pricing_question"))
        enough_to_advise = bool(normalized_profile.get("target_category")) and bool(
            normalized_profile.get("target_platform")
            or normalized_profile.get("budget_range")
            or normalized_profile.get("target_audience")
            or (memory_context or {}).get("recent_user_transcript")
        )

        if pricing_ready:
            is_complete = True
            missing_fields = []
            should_enter_consulting = True
            consulting_reason = consulting_reason or "用户正在询问定价判断，应先结合已有资料和合理假设进入咨询，而不是继续追问。"
        elif should_enter_consulting and enough_to_advise:
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
        local_result = self._extract_locally(user_input, memory_context=memory_context)
        if local_result:
            return local_result

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

    def _extract_locally(
        self,
        user_input: str,
        memory_context: dict[str, Any] | None = None,
    ) -> RequirementResult | None:
        text = user_input.strip()
        if not text:
            return None

        profile = {
            "task_type": _detect_task_type(text),
            "target_platform": _find_first(text, PLATFORM_HINTS),
            "target_category": _find_category(text),
            "budget_range": _find_budget(text),
            "target_audience": _find_audience(text),
            "content_style": _find_first(text, CONTENT_STYLE_HINTS),
            "sales_goal": _find_sales_goal(text),
            "risk_preference": _find_first(text, RISK_HINTS),
            "pricing_question": text if _is_pricing_text(text) else None,
            "price_reference": _find_price_reference(text),
            "known_constraints": _find_constraints(text),
        }

        if not profile["target_platform"]:
            profile["target_platform"] = _first_memory_value(memory_context, "preferences", PLATFORM_HINTS)
        if not profile["target_category"]:
            profile["target_category"] = _first_memory_value(memory_context, "preferences", CATEGORY_HINTS)
        if not profile["target_audience"] and (memory_context or {}).get("recent_user_transcript"):
            profile["target_audience"] = "参考当前会话中的目标用户信息"

        has_advice_intent = any(word in text for word in ADVICE_HINTS)
        has_enough_fields = bool(profile["target_category"]) and bool(
            profile["target_platform"] or profile["budget_range"] or profile["target_audience"]
        )
        if not has_enough_fields and not profile["pricing_question"]:
            return None

        return self.normalize_result(
            {
                "is_complete": True,
                "requirement_profile": profile,
                "missing_fields": [],
                "should_enter_consulting": True,
                "consulting_reason": "本地规则已识别到足够的运营需求信息，直接进入咨询以减少需求抽取模型调用。",
                "follow_up_question": "",
                "process_message": (
                    "我已快速整理出平台、类目、预算或目标用户等关键信息，"
                    "可以直接进入建议生成。"
                    if has_advice_intent
                    else "我已快速整理出当前需求，可以进入下一步分析。"
                ),
            },
            memory_context=memory_context,
        )


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


PLATFORM_HINTS = ["小红书", "抖音", "快手", "淘宝", "天猫", "拼多多", "TikTok", "Amazon", "亚马逊", "京东"]
CATEGORY_HINTS = [
    "二次元周边",
    "二次元",
    "谷子",
    "家居收纳",
    "收纳",
    "女包",
    "美妆",
    "护肤",
    "宠物用品",
    "宠物",
    "甜品",
    "泡芙",
    "服饰",
    "食品",
    "数码",
    "母婴",
]
CONTENT_STYLE_HINTS = ["种草", "短视频", "直播", "图文", "笔记", "探店", "测评"]
RISK_HINTS = ["低库存", "轻库存", "低风险", "小批量", "不囤货", "可接受囤货"]
ADVICE_HINTS = ["帮我", "建议", "方案", "判断", "分析", "推荐", "怎么", "如何", "选品", "定价"]


def _detect_task_type(text: str) -> str:
    if _is_pricing_text(text):
        return "pricing_strategy"
    if any(word in text for word in ["脚本", "内容", "笔记", "种草", "短视频", "直播"]):
        return "content_advice"
    if any(word in text for word in ["流量", "趋势", "热度", "搜索", "曝光"]):
        return "traffic_analysis"
    if any(word in text for word in ["平台", "淘宝", "天猫", "京东", "拼多多", "TikTok", "Amazon", "亚马逊"]):
        return "platform_strategy"
    return "product_selection"


def _is_pricing_text(text: str) -> bool:
    return any(word in text for word in ["定价", "价格", "原价", "折扣", "毛利", "利润", "客单价", "%"])


def _find_first(text: str, candidates: list[str]) -> str | None:
    lowered = text.lower()
    for candidate in candidates:
        if candidate.lower() in lowered:
            return candidate
    return None


def _find_category(text: str) -> str | None:
    return _find_first(text, CATEGORY_HINTS)


def _find_budget(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*([万千kK]?)\s*元?", text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "万":
        value *= 10000
    elif unit in {"千", "k", "K"}:
        value *= 1000
    return value


def _find_audience(text: str) -> str | None:
    patterns = [
        r"目标(?:用户|人群)?[是为:]?([^，。,.；;]+)",
        r"面向([^，。,.；;]+)",
        r"给([^，。,.；;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            if value:
                return value[:40]
    for keyword in ["学生党", "租房女生", "通勤白领", "上班族", "宝妈", "抹茶控", "年轻女性"]:
        if keyword in text:
            return keyword
    return None


def _find_sales_goal(text: str) -> str | None:
    if any(word in text for word in ["测试", "测品", "小流量"]):
        return "低成本测试新品"
    if any(word in text for word in ["开店", "起号"]):
        return "开店起号"
    if any(word in text for word in ["复购", "留存"]):
        return "提高复购"
    return "获取运营建议" if any(word in text for word in ADVICE_HINTS) else None


def _find_price_reference(text: str) -> dict[str, Any] | None:
    ratios = re.findall(r"\d+(?:\.\d+)?\s*%", text)
    if not ratios:
        return None
    return {"base_price": "原价" if "原价" in text else "参考价", "ratio_options": ratios}


def _find_constraints(text: str) -> list[str]:
    constraints = []
    for keyword in ["低库存", "轻库存", "低成本", "小预算", "小流量", "不囤货"]:
        if keyword in text:
            constraints.append(keyword)
    return constraints


def _first_memory_value(memory_context: dict[str, Any] | None, key: str, candidates: list[str]) -> str | None:
    values = (memory_context or {}).get(key) or []
    if not isinstance(values, list):
        return None
    for value in values:
        matched = _find_first(str(value), candidates)
        if matched:
            return matched
    return None
