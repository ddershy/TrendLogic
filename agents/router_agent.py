from __future__ import annotations

from dataclasses import dataclass

from .base_agent import BaseAgent


@dataclass
class RouterDecision:
    in_scope: bool
    intent: str
    confidence: float
    next_agent: str
    reason: str


class RouterAgent(BaseAgent):
    name = "分类决策Agent"

    INTENT_KEYWORDS = {
        "product_selection": ["选品", "商品", "爆品", "卖什么", "类目", "货源", "上新"],
        "traffic_analysis": ["流量", "趋势", "热度", "搜索", "曝光", "转化"],
        "content_advice": ["带货", "短视频", "笔记", "种草", "脚本", "内容", "小红书", "抖音"],
        "user_growth": ["召回", "用户", "增长", "复购", "画像", "留存"],
        "platform_strategy": ["淘宝", "天猫", "京东", "TikTok", "Amazon", "亚马逊", "拼多多"],
    }

    def run(self, user_input: str) -> RouterDecision:
        text = user_input.lower()
        best_intent = "unknown"
        best_score = 0
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > best_score:
                best_intent = intent
                best_score = score
        in_scope = best_score > 0
        return RouterDecision(
            in_scope=in_scope,
            intent=best_intent if in_scope else "out_of_scope",
            confidence=min(0.55 + best_score * 0.14, 0.96) if in_scope else 0.25,
            next_agent="requirement_agent" if in_scope else "final",
            reason="用户问题命中了电商运营相关关键词" if in_scope else "未识别到电商运营、选品、流量或用户增长相关目标",
        )
