from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .llm_client import LLMClient


USER_PROFILE_PROMPT = """
你是 TrendLogic 的用户画像 Agent。

你的任务是把用户的近期对话、长期记忆和偏好沉淀成“可运营”的用户画像。
请注意：
- 画像不是聊天回复，不要和用户闲聊；
- 不要臆造不存在的信息，不确定时降低 confidence；
- 类目、平台、预算、负向偏好、经营目标都要尽量结构化；
- 输出只能是 JSON，不要 Markdown。

JSON 格式：
{
  "profile_summary": "一句话概括用户当前经营状态和关注点",
  "long_term_summary": "压缩后的长期记忆摘要，保留稳定偏好和经营需求",
  "preferred_categories": ["二次元周边"],
  "preferred_platforms": ["小红书"],
  "interest_weights": {"二次元周边": 0.82, "小红书": 0.76},
  "negative_preferences": ["不希望一开始重库存"],
  "business_needs": ["用 5000 元预算做小红书选品测试"],
  "behavior_notes": ["会主动询问预算分配和选品建议"],
  "tags": ["小红书", "二次元周边", "低库存测试"],
  "recall_score": 0.72,
  "confidence": 0.78,
  "update_reason": "根据最近会话和长期记忆更新"
}
""".strip()


PLATFORM_HINTS = ["小红书", "抖音", "快手", "淘宝", "天猫", "拼多多", "视频号", "TikTok", "Amazon", "独立站"]
CATEGORY_HINTS = [
    "二次元",
    "谷子",
    "美妆",
    "护肤",
    "女包",
    "箱包",
    "收纳",
    "家居",
    "数码",
    "宠物",
    "母婴",
    "食品",
    "服饰",
    "运动",
    "户外",
    "跨境",
]
OPERATION_HINTS = ["低成本", "低风险", "预算", "选品", "爆品", "召回", "复购", "短视频", "内容种草", "开店"]


@dataclass
class UserProfileUpdatePlan:
    profile_summary: str = ""
    long_term_summary: str = ""
    preferred_categories: list[str] = field(default_factory=list)
    preferred_platforms: list[str] = field(default_factory=list)
    interest_weights: dict[str, float] = field(default_factory=dict)
    negative_preferences: list[str] = field(default_factory=list)
    business_needs: list[str] = field(default_factory=list)
    behavior_notes: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    recall_score: float = 0.0
    confidence: float = 0.7
    update_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_summary": self.profile_summary,
            "long_term_summary": self.long_term_summary,
            "preferred_categories": self.preferred_categories,
            "preferred_platforms": self.preferred_platforms,
            "interest_weights": self.interest_weights,
            "negative_preferences": self.negative_preferences,
            "business_needs": self.business_needs,
            "behavior_notes": self.behavior_notes,
            "tags": self.tags,
            "recall_score": self.recall_score,
            "confidence": self.confidence,
            "update_reason": self.update_reason,
        }


class UserProfileAgent:
    name = "用户画像Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        try:
            self.llm_client = llm_client or LLMClient()
        except Exception:
            self.llm_client = None

    def analyze(
        self,
        *,
        user: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
        recent_sessions: list[dict[str, Any]] | None = None,
    ) -> UserProfileUpdatePlan:
        payload = {
            "user": user or {},
            "memory_context": memory_context or {},
            "recent_sessions": recent_sessions or [],
        }
        if self.llm_client and self.llm_client.is_configured:
            try:
                raw = self.llm_client.chat_json(
                    [
                        {"role": "system", "content": USER_PROFILE_PROMPT},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ]
                )
                return self.normalize_plan(raw, payload)
            except Exception:
                pass
        return self._fallback_plan(payload)

    def extract_tags(self, text: str) -> list[str]:
        """Lightweight tag extraction used during normal chat writes."""

        normalized = text.strip()
        if not normalized:
            return []
        tags = []
        for keyword in [*PLATFORM_HINTS, *CATEGORY_HINTS, *OPERATION_HINTS]:
            if keyword.lower() in normalized.lower():
                tags.append(keyword)
        budget_match = re.search(r"(\d+(?:\.\d+)?\s*[万千kK]?\s*元?)", normalized)
        if budget_match and any(word in normalized for word in ["预算", "本金", "投入", "成本"]):
            tags.append("预算敏感")
        return _unique(tags)

    def normalize_plan(self, raw: dict[str, Any], payload: dict[str, Any]) -> UserProfileUpdatePlan:
        fallback = self._fallback_plan(payload)
        plan = UserProfileUpdatePlan(
            profile_summary=str(raw.get("profile_summary") or fallback.profile_summary).strip(),
            long_term_summary=str(raw.get("long_term_summary") or fallback.long_term_summary).strip(),
            preferred_categories=_ensure_list(raw.get("preferred_categories")) or fallback.preferred_categories,
            preferred_platforms=_ensure_list(raw.get("preferred_platforms")) or fallback.preferred_platforms,
            interest_weights=_normalize_weights(raw.get("interest_weights")) or fallback.interest_weights,
            negative_preferences=_ensure_list(raw.get("negative_preferences")) or fallback.negative_preferences,
            business_needs=_ensure_list(raw.get("business_needs")) or fallback.business_needs,
            behavior_notes=_ensure_list(raw.get("behavior_notes")) or fallback.behavior_notes,
            tags=_ensure_list(raw.get("tags")) or fallback.tags,
            recall_score=_clamp_float(raw.get("recall_score"), fallback.recall_score),
            confidence=_clamp_float(raw.get("confidence"), fallback.confidence),
            update_reason=str(raw.get("update_reason") or fallback.update_reason).strip(),
        )
        plan.tags = _unique([*plan.tags, *plan.preferred_categories, *plan.preferred_platforms])
        return plan

    def _fallback_plan(self, payload: dict[str, Any]) -> UserProfileUpdatePlan:
        memory_context = payload.get("memory_context") or {}
        sessions = payload.get("recent_sessions") or []
        text = "\n".join(
            str(item.get("user_transcript") or item.get("session_summary") or "")
            for item in sessions
            if isinstance(item, dict)
        )
        tags = _unique(
            [
                *self.extract_tags(text),
                *_ensure_list(memory_context.get("tags")),
                *_ensure_list(memory_context.get("preferences")),
            ]
        )
        platforms = [tag for tag in tags if tag in PLATFORM_HINTS]
        categories = [tag for tag in tags if tag in CATEGORY_HINTS or tag.endswith("周边")]
        business_needs = _ensure_list(memory_context.get("business_needs"))
        if not business_needs and text:
            business_needs = [text.replace("\n", " ")[:120]]

        summary_bits = []
        if platforms:
            summary_bits.append(f"关注平台：{', '.join(platforms[:3])}")
        if categories:
            summary_bits.append(f"关注类目：{', '.join(categories[:3])}")
        if business_needs:
            summary_bits.append(f"经营需求：{business_needs[0]}")
        profile_summary = "；".join(summary_bits) or str(memory_context.get("user_profile_summary") or "用户画像信息仍在积累中。")
        long_term_summary = str(memory_context.get("long_term_summary") or "").strip()
        if text:
            long_term_summary = _join_text(long_term_summary, text.replace("\n", " ")[:360])
        weights = {tag: 0.68 for tag in tags[:12]}
        return UserProfileUpdatePlan(
            profile_summary=profile_summary,
            long_term_summary=long_term_summary or profile_summary,
            preferred_categories=_unique(categories),
            preferred_platforms=_unique(platforms),
            interest_weights=weights,
            negative_preferences=_ensure_list(memory_context.get("negative_preferences")),
            business_needs=business_needs[:8],
            behavior_notes=["用户近期有电商运营咨询行为。"] if sessions else [],
            tags=tags[:20],
            recall_score=min(0.35 + len(tags) * 0.04 + len(sessions) * 0.03, 0.95),
            confidence=0.62 if tags or sessions else 0.45,
            update_reason="模型不可用时，根据近期会话和记忆上下文生成基础画像。",
        )


def _ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_weights(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    weights: dict[str, float] = {}
    for key, raw_score in value.items():
        label = str(key).strip()
        if label:
            weights[label] = _clamp_float(raw_score, 0.5)
    return weights


def _clamp_float(value: object, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return max(0.0, min(number, 1.0))


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _join_text(existing: str, addition: str, limit: int = 2000) -> str:
    if not addition:
        return existing[-limit:]
    if not existing:
        return addition[-limit:]
    if addition in existing:
        return existing[-limit:]
    return f"{existing}\n{addition}"[-limit:]
