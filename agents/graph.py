"""
LangGraph流程控制图
"""

from __future__ import annotations
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, END
from .router_agent import RouterAgent
from .requirement_agent import RequirementAgent
from .product_consultant_agent import ProductConsultantAgent

# 图状态
class AgentState(TypedDict):
    user_input: str
    memory_context: NotRequired[dict]
    router_decision: NotRequired[dict]
    requirement_result: NotRequired[dict]
    memory_candidates: NotRequired[list[dict]]
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
    result = requirement_agent.run(state["user_input"], state.get("memory_context"))

    process_message = {
        "type": "process",
        "agent": "需求分析Agent",
        "content": result.process_message,
    }

    memory_candidates = build_requirement_memory_candidates(result.requirement_profile)

    return {
        **state,
        "requirement_result": {
            "is_complete": result.is_complete,
            "requirement_profile": result.requirement_profile,
            "missing_fields": result.missing_fields,
            "follow_up_question": result.follow_up_question,
            "should_enter_consulting": result.should_enter_consulting,
            "consulting_reason": result.consulting_reason,
        },
        "memory_candidates": state.get("memory_candidates", []) + memory_candidates,
        "messages": state.get("messages", []) + [process_message],
    }


def route_after_requirement(state: AgentState) -> str:
    result = state["requirement_result"]
    if not result["is_complete"]:
        return "ask_follow_up"
    return "product_consultant"


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


def product_consultant_node(state: AgentState) -> AgentState:
    consultant = ProductConsultantAgent()
    profile = state.get("requirement_result", {}).get("requirement_profile", {})
    result = consultant.run(profile, state.get("memory_context"), user_input=state["user_input"])
    process_message = {
        "type": "process",
        "agent": "选品咨询Agent",
        "content": result.process_message,
    }
    final_message = {
        "type": "final",
        "agent": "选品咨询Agent",
        "content": result.final_message,
    }

    return {
        **state,
        "memory_candidates": state.get("memory_candidates", []) + result.memory_candidates,
        "messages": state.get("messages", []) + [process_message, final_message],
    }


def build_requirement_memory_candidates(profile: dict) -> list[dict]:
    candidates = []
    platform = profile.get("target_platform")
    category = profile.get("target_category")
    budget = profile.get("budget_range")
    audience = profile.get("target_audience")
    risk_preference = profile.get("risk_preference")
    sales_goal = profile.get("sales_goal")

    preference_parts = [value for value in [platform, category, risk_preference] if value]
    if preference_parts:
        candidates.append(
            {
                "candidate_type": "preference",
                "content": "；".join(str(value) for value in preference_parts),
                "source_agent": "requirement_agent",
                "confidence": 0.72,
                "tags": [str(value) for value in preference_parts],
            }
        )
    need_parts = []
    if sales_goal:
        need_parts.append(f"目标：{sales_goal}")
    if audience:
        need_parts.append(f"目标用户：{audience}")
    if budget:
        need_parts.append(f"预算：{budget}")
    if need_parts:
        candidates.append(
            {
                "candidate_type": "business_need",
                "content": "；".join(str(value) for value in need_parts),
                "source_agent": "requirement_agent",
                "confidence": 0.68,
                "tags": [str(value) for value in [platform, category] if value],
            }
        )
    return candidates


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("router", router_node)
    graph.add_node("out_of_scope", out_of_scope_node)
    graph.add_node("requirement_node", requirement_node)
    graph.add_node("ask_follow_up", ask_follow_up_node)
    graph.add_node("product_consultant", product_consultant_node)

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
            "product_consultant": "product_consultant",
        },
    )
    graph.add_edge("ask_follow_up", END)
    graph.add_edge("product_consultant", END)

    return graph.compile()


class TrendLogicGraph:
    def __init__(self):
        self.graph = build_graph()

    def run(self, user_input: str, memory_context: dict | None = None) -> dict:
        return self.graph.invoke(
            {
                "user_input": user_input,
                "memory_context": memory_context or {},
                "memory_candidates": [],
                "messages": [],
            }
        )

    def run_steps(self, user_input: str, memory_context: dict | None = None):
        state: AgentState = {
            "user_input": user_input,
            "memory_context": memory_context or {},
            "memory_candidates": [],
            "messages": [],
        }
        message_count = 0

        yield _status_payload("router", "我正在识别你的问题属于哪个运营场景。")
        state = router_node(state)
        yield _step_payload("router", state, message_count)
        message_count = len(state.get("messages", []))

        if route_after_router(state) == "out_of_scope":
            yield _status_payload("out_of_scope", "我会给出话题范围提示，避免你继续等无关流程。")
            state = out_of_scope_node(state)
            yield _step_payload("out_of_scope", state, message_count)
            return state

        yield _status_payload("requirement_node", "我正在提取平台、类目、预算、目标用户和经营目标。")
        state = requirement_node(state)
        yield _step_payload("requirement_node", state, message_count)
        message_count = len(state.get("messages", []))

        if route_after_requirement(state) == "ask_follow_up":
            yield _status_payload("ask_follow_up", "我会只追问当前最关键的缺口，尽量减少打扰。")
            state = ask_follow_up_node(state)
            yield _step_payload("ask_follow_up", state, message_count)
            return state

        yield _status_payload("product_consultant", "我正在结合需求、记忆和工具结果生成选品建议。")
        state = product_consultant_node(state)
        yield _step_payload("product_consultant", state, message_count)
        return state


def _status_payload(node: str, content: str) -> dict:
    return {
        "node": node,
        "state": None,
        "new_messages": [
            {
                "type": "process",
                "agent": "TrendLogic",
                "function": "执行进度",
                "content": content,
            }
        ],
        "ephemeral": True,
    }


def _step_payload(node: str, state: AgentState, previous_message_count: int) -> dict:
    return {
        "node": node,
        "state": state,
        "new_messages": state.get("messages", [])[previous_message_count:],
    }
