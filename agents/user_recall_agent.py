from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .llm_client import LLMClient


RECALL_GENERATION_PROMPT = """
你是 TrendLogic 的用户召回 Agent。

你的任务是根据用户画像、记忆和近期爆品，生成一条适合运营人员发送给用户的召回文案。
要求：
- 站在用户经营目标的角度写，不要像广告群发；
- 召回理由要和用户偏好、经营需求、近期趋势有明确关系；
- 如果信息不足，要保守，不要编造具体销量或平台数据；
- 输出只能是 JSON，不要 Markdown。

JSON 格式：
{
  "recall_score": 0.82,
  "matched_trends": ["亚克力挂件", "吧唧套装"],
  "reason": "用户近期关注小红书二次元周边，爆品库中存在匹配趋势。",
  "message": "给用户发送的召回文案",
  "recommended_channel": "站内信/微信",
  "timing": "今天内发送"
}
""".strip()


@dataclass
class RecallAssessment:
    user_id: str
    display_name: str
    account_id: str
    preferred_categories: list[str] = field(default_factory=list)
    recall_score: float = 0.0
    reason: str = ""
    last_active_at: str | None = None
    matched_trends: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "account_id": self.account_id,
            "preferred_categories": self.preferred_categories,
            "recall_score": self.recall_score,
            "reason": self.reason,
            "last_active_at": self.last_active_at,
            "matched_trends": self.matched_trends,
        }


@dataclass
class RecallGeneration:
    recall_score: float
    matched_trends: list[str]
    reason: str
    message: str
    recommended_channel: str = ""
    timing: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "recall_score": self.recall_score,
            "matched_trends": self.matched_trends,
            "reason": self.reason,
            "message": self.message,
            "recommended_channel": self.recommended_channel,
            "timing": self.timing,
        }


class RecallAgent:
    name = "用户召回Agent"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        try:
            self.llm_client = llm_client or LLMClient()
        except Exception:
            self.llm_client = None

    def assess_candidate(
        self,
        *,
        user: dict[str, Any],
        profile: dict[str, Any] | None = None,
        memory: dict[str, Any] | None = None,
        trends: list[dict[str, Any]] | None = None,
    ) -> RecallAssessment:
        profile = profile or {}
        memory = memory or {}
        trends = trends or []
        preferred_categories = _unique(
            [
                *_ensure_list(profile.get("preferred_categories")),
                *_preference_values(memory.get("preferences")),
                *_ensure_list(memory.get("tags")),
            ]
        )
        matched_trends = _match_trends(preferred_categories, trends)
        interaction_frequency = int(profile.get("interaction_frequency") or 0)
        base_score = 0.28 + min(interaction_frequency, 8) * 0.035 + len(preferred_categories[:6]) * 0.035
        if matched_trends:
            base_score += 0.18
        if memory.get("business_needs"):
            base_score += 0.08
        recall_score = _clamp(base_score)
        reason_parts = []
        if preferred_categories:
            reason_parts.append(f"用户偏好集中在 {', '.join(preferred_categories[:3])}")
        if matched_trends:
            reason_parts.append(f"近期爆品中匹配到 {', '.join(matched_trends[:3])}")
        if memory.get("business_needs"):
            reason_parts.append("已有明确经营需求可承接")
        reason = "；".join(reason_parts) or "用户画像信息较少，建议先做低打扰召回。"
        return RecallAssessment(
            user_id=str(user.get("id") or ""),
            display_name=str(user.get("display_name") or ""),
            account_id=str(user.get("account_id") or ""),
            preferred_categories=preferred_categories[:8],
            recall_score=round(recall_score, 2),
            reason=reason,
            last_active_at=user.get("last_active_at") or profile.get("last_active_at"),
            matched_trends=matched_trends[:5],
        )

    def generate(
        self,
        display_name: str,
        categories: list[str] | None = None,
        trends: list[str] | None = None,
        score: float | None = None,
        *,
        profile: dict[str, Any] | None = None,
        memory: dict[str, Any] | None = None,
        trending_items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        categories = categories or []
        trends = trends or []
        trend_payload = trending_items or [{"title": title, "category": "", "summary": ""} for title in trends]
        payload = {
            "display_name": display_name,
            "categories": categories,
            "profile": profile or {},
            "memory": memory or {},
            "trending_items": trend_payload,
            "candidate_score": score,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        if self.llm_client and self.llm_client.is_configured:
            try:
                raw = self.llm_client.chat_json(
                    [
                        {"role": "system", "content": RECALL_GENERATION_PROMPT},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ]
                )
                return self.normalize_generation(raw, payload).to_dict()
            except Exception:
                pass
        return self._fallback_generation(payload).to_dict()

    def normalize_generation(self, raw: dict[str, Any], payload: dict[str, Any]) -> RecallGeneration:
        fallback = self._fallback_generation(payload)
        return RecallGeneration(
            recall_score=round(_clamp(raw.get("recall_score"), fallback.recall_score), 2),
            matched_trends=_ensure_list(raw.get("matched_trends")) or fallback.matched_trends,
            reason=str(raw.get("reason") or fallback.reason).strip(),
            message=str(raw.get("message") or fallback.message).strip(),
            recommended_channel=str(raw.get("recommended_channel") or fallback.recommended_channel).strip(),
            timing=str(raw.get("timing") or fallback.timing).strip(),
        )

    def _fallback_generation(self, payload: dict[str, Any]) -> RecallGeneration:
        display_name = str(payload.get("display_name") or "你好").strip()
        categories = _ensure_list(payload.get("categories"))
        memory = payload.get("memory") if isinstance(payload.get("memory"), dict) else {}
        if not categories:
            categories = _preference_values(memory.get("preferences")) or _ensure_list(memory.get("tags"))
        trends = payload.get("trending_items") if isinstance(payload.get("trending_items"), list) else []
        trend_titles = [str(item.get("title") or "").strip() for item in trends if isinstance(item, dict) and item.get("title")]
        matched_trends = _match_trends(categories, trends) or trend_titles[:3]
        category = categories[0] if categories else "你关注的方向"
        trend = matched_trends[0] if matched_trends else "近期热门选品"
        score = _clamp(payload.get("candidate_score"), 0.58)
        reason = f"用户历史偏好与 {trend} 存在关联，可用具体趋势重新激活经营需求。"
        message = (
            f"{display_name}，我看到最近“{trend}”相关方向有新的内容机会，"
            f"和你之前关注的“{category}”比较接近。"
            "如果你还想继续做低风险选品测试，可以回来看看这批趋势，我可以帮你把预算、SKU 和内容切入角度一起拆出来。"
        )
        return RecallGeneration(
            recall_score=round(score, 2),
            matched_trends=matched_trends[:3],
            reason=reason,
            message=message,
            recommended_channel="站内信",
            timing="用户 3-7 天未活跃时发送",
        )


def _ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _preference_values(value: object) -> list[str]:
    if isinstance(value, dict):
        result: list[str] = []
        for item in value.values():
            result.extend(_ensure_list(item))
        return result
    return _ensure_list(value)


def _match_trends(categories: list[str], trends: list[dict[str, Any]]) -> list[str]:
    matched: list[str] = []
    lowered_categories = [item.lower() for item in categories]
    for trend in trends:
        if not isinstance(trend, dict):
            continue
        title = str(trend.get("title") or "").strip()
        category = str(trend.get("category") or "").strip()
        summary = str(trend.get("summary") or "").strip()
        haystack = f"{title} {category} {summary}".lower()
        if not title:
            continue
        if not lowered_categories or any(label and label.lower() in haystack for label in lowered_categories):
            matched.append(title)
    return _unique(matched)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _clamp(value: object, fallback: float = 0.5) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return max(0.0, min(number, 0.98))
