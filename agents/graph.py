"""
LangGraph流程控制图
"""

from __future__ import annotations
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, END
from .router_agent import RouterAgent
from .requirement_agent import RequirementAgent

# 图状态
class AgentState(TypedDict):
    user_input: str
    router_decision: NotRequired[dict]
    requirement_result: NotRequired[dict]
    messages: list[dict]


def router_node(state: AgentState) -> AgentState: # 判断是否在业务范围
    router = RouterAgent()
    decision = router.run(state["user_input"])

    process_message = {
        "type": "process",
        "agent": "分类决策Agent",
        "content": decision.process_message or f"我已经判断用户问题属于：{decision.intent}。",
    }

    return {
        **state,
        "router_decision": {
            "in_scope": decision.in_scope,
            "intent": decision.intent,
            "confidence": decision.confidence,
            "next_agent": decision.next_agent,
            "reason": decision.reason,
        },
        "messages": state.get("messages", []) + [process_message],
    }


def route_after_router(state: AgentState) -> str: # 条件边，在范围则询问需求，不在则退出
    decision = state["router_decision"]

    if not decision["in_scope"]:
        return "out_of_scope"

    return "requirement_node"


def out_of_scope_node(state: AgentState) -> AgentState: # 不在范围
    final_message = {
        "type": "final",
        "agent": "TrendLogic",
        "content": (
            "这个话题和 TrendLogic 的电商运营任务无关。"
            "你可以描述你想做的商品、平台、目标用户或运营问题，我会继续帮你分析。"
        ),
    }

    return {
        **state,
        "messages": state.get("messages", []) + [final_message],
    }


def requirement_node(state: AgentState) -> AgentState: # 需求节点，询问内容并分析需求
    requirement_agent = RequirementAgent()
    result = requirement_agent.run(state["user_input"])

    process_message = {
        "type": "process",
        "agent": "需求分析Agent",
        "content": result.process_message,
    }

    return {
        **state,
        "requirement_result": {
            "is_complete": result.is_complete,
            "requirement_profile": result.requirement_profile,
            "missing_fields": result.missing_fields,
            "follow_up_question": result.follow_up_question,
        },
        "messages": state.get("messages", []) + [process_message],
    }


def route_after_requirement(state: AgentState) -> str:
    result = state["requirement_result"]
    if not result["is_complete"]:
        return "ask_follow_up"
    return "product_placeholder"


def ask_follow_up_node(state: AgentState) -> AgentState:
    result = state["requirement_result"]
    final_message = {
        "type": "final",
        "agent": "TrendLogic",
        "content": result["follow_up_question"],
    }

    return {
        **state,
        "messages": state.get("messages", []) + [final_message],
    }


def product_placeholder_node(state: AgentState) -> AgentState:
    final_message = {
        "type": "final",
        "agent": "TrendLogic",
        "content": (
            "我已经完成需求分析。下一步会进入选品咨询 Agent，结合爆品、用户记忆和业务目标生成建议。"
        ),
    }

    return {
        **state,
        "messages": state.get("messages", []) + [final_message],
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("out_of_scope", out_of_scope_node)
    graph.add_node("requirement_node", requirement_node)
    graph.add_node("ask_follow_up", ask_follow_up_node)
    graph.add_node("product_placeholder", product_placeholder_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "out_of_scope": "out_of_scope",
            "requirement_node": "requirement_node",
        },
    )

    graph.add_edge("out_of_scope", END)
    graph.add_conditional_edges(
        "requirement_node",
        route_after_requirement,
        {
            "ask_follow_up": "ask_follow_up",
            "product_placeholder": "product_placeholder",
        },
    )
    graph.add_edge("ask_follow_up", END)
    graph.add_edge("product_placeholder", END)

    return graph.compile()


class TrendLogicGraph:
    def __init__(self):
        self.graph = build_graph()

    def run(self, user_input: str) -> dict:
        return self.graph.invoke(
            {
                "user_input": user_input,
                "messages": [],
            }
        )
