"""
LangGraph流程控制图
"""

from __future__ import annotations
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, END
from .router_agent import RouterAgent

# 图状态
class AgentState(TypedDict):
    user_input: str
    router_decision: NotRequired[dict]
    messages: list[dict]


def router_node(state: AgentState) -> AgentState:
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


# 条件边
def route_after_router(state: AgentState) -> str:
    decision = state["router_decision"]

    if not decision["in_scope"]:
        return "out_of_scope"

    return "need_requirement"


def out_of_scope_node(state: AgentState) -> AgentState:
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


def requirement_placeholder_node(state: AgentState) -> AgentState:
    final_message = {
        "type": "final",
        "agent": "TrendLogic",
        "content": (
            "我已经识别到这是电商运营相关问题。"
            "下一步会进入需求分析 Agent，用来补全平台、预算、类目和目标用户。"
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
    graph.add_node("need_requirement", requirement_placeholder_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "out_of_scope": "out_of_scope",
            "need_requirement": "need_requirement",
        },
    )

    graph.add_edge("out_of_scope", END)
    graph.add_edge("need_requirement", END)

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
