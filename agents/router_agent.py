"""
RouterAgent是一个分类决策Agent，负责根据用户输入的文本内容判断用户的意图，并将问题路由到相应的其余Agent进行处理。
它通过一个agent来决策
"""
from __future__ import annotations
from dataclasses import dataclass
from .llm_client import LLMClient

ALLOWED_INTENTS = {
    "product_selection", #选品
    "traffic_analysis", #流量趋势分析
    "content_advice", #内容带货建议
    "trending_analysis", #趋势分析
    "user_profile", #用户画像
    "recall_strategy", #用户召回
    "platform_strategy", #平台策略
    "out_of_scope", #不在业务范围内
}

NEXT_AGENT_MAP = {
    "product_selection": "requirement_agent",
    "traffic_analysis": "requirement_agent",
    "content_advice": "requirement_agent",
    "trending_analysis": "product_consultant_agent",
    "user_profile": "user_profile_agent",
    "recall_strategy": "user_recall_agent",
    "platform_strategy": "requirement_agent",
    "out_of_scope": "final",
}

ROUTER_AGENT_PROMPT = (
"""
你是一个分类决策Agent，负责判断用户输入的文本内容是否与电商运营相关，并识别用户的具体意图。你的任务是将用户的问题路由到最合适的后续Agent进行处理，并拒绝用户的无关话题。
业务范围包括：
- 选品分析（product_selection）：帮助用户分析和选择适合的商品进行销售。
- 流量趋势分析（traffic_analysis）：分析电商平台的流量趋势，帮助用户把握市场动态。
- 内容带货建议（content_advice）：提供关于如何通过内容（如短视频、笔记等）进行带货的建议。
- 趋势分析（trending_analysis）：分析当前的市场趋势，帮助用户把握热点机会。
- 用户画像（user_profile）：帮助用户分析目标用户的画像和需求。
- 用户召回（recall_strategy）：提供用户召回的策略建议，帮助用户提升用户留存和复购。
- 平台策略（platform_strategy）：提供针对不同电商平台（如淘宝、京东、TikTok等）的运营策略建议。
而"process_message":中返回的是你认为可以给用户看到的内容，也就是正在分析的这个问题的意图和相关信息，帮助用户理解你是如何判断的，以及为什么要路由到这个Agent的。


如如果用户只是闲聊、问天气、写代码、讲故事、学习无关知识，不涉及上述任何一个业务目标，请判断为“out_of_scope”，并拒绝继续分派给后续Agent，避免给出偏题建议。+

你只能输出 JSON，不要输出 Markdown，不要解释。

JSON 格式：
{
  "in_scope": true,
  "intent": "product_selection",
  "confidence": 0.86,
  "next_agent": "requirement_agent",
  "reason": "用户正在询问适合售卖的商品方向",
  "process_message": "我先判断这个问题是否属于电商运营任务。当前问题和选品咨询有关，可以进入需求补全流程。"
}
""")

@dataclass
class RouterDecision:
    """
    RouterAgent的输入内容
    """
    in_scope: bool
    intent: str
    confidence: float
    next_agent: str | None
    reason: str #给系统看
    process_message: str #给用户看



class RouterAgent():
    """
    RouterAgent负责根据用户输入的文本内容判断用户的意图，并将问题路由到相应的其余Agent进行处理。
    """
    name = "分类决策Agent"

    INTENT_KEYWORDS = {
        "product_selection": ["选品", "商品", "爆品", "卖什么", "类目", "货源", "上新"],
        "traffic_analysis": ["流量", "趋势", "热度", "搜索", "曝光", "转化"],
        "content_advice": ["带货", "短视频", "笔记", "种草", "脚本", "内容", "小红书", "抖音"],
        "user_growth": ["召回", "用户", "增长", "复购", "画像", "留存"],
        "platform_strategy": ["淘宝", "天猫", "京东", "TikTok", "Amazon", "亚马逊", "拼多多"],
    }

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def normalize_decision(self, result: dict) -> RouterDecision: #将模型的输出规范化成RouterDecision对象
        intent = result.get("intent", "out_of_scope")

        if intent not in ALLOWED_INTENTS:
            intent = "out_of_scope"
        
        in_scope = bool(result.get("in_scope", intent != "out_of_scope"))

        if intent == "out_of_scope":
            in_scope = False
        
        try:
            confidence = float(result.get("confidence", 0.0))
        except (ValueError, TypeError):
            confidence = 0.5
        
        confidence = max(0.0, min(1.0, confidence))

        next_agent = result.get("next_agent") or NEXT_AGENT_MAP[intent]
        if next_agent not in NEXT_AGENT_MAP.values():
            next_agent = NEXT_AGENT_MAP[intent]
        
        reason = result.get("reason", "模型完成了意图分类。")
        process_message = result.get("process_message", "")
        if not process_message:
            process_message = f"我已经判断用户问题属于：{intent}。"

        return RouterDecision(
            in_scope=in_scope,
            intent=intent,
            confidence=confidence,
            next_agent=next_agent,
            reason=reason,
            process_message=process_message
        )


    def run(self, user_input: str) -> RouterDecision:
        messages = [
               {"role": "system","content": ROUTER_AGENT_PROMPT},
               {"role": "user","content": user_input},
        ]
        result = self.llm_client.chat_json(messages)

        return self.normalize_decision(result)
