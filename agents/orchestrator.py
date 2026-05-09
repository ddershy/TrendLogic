from __future__ import annotations

from dataclasses import asdict

from .base_agent import AgentFinal, AgentTrace
from .product_consultant_agent import ProductConsultantAgent
from .requirement_agent import RequirementAgent
from .router_agent import RouterAgent


class AgentOrchestrator:
    def __init__(self) -> None:
        self.router = RouterAgent()
        self.requirement = RequirementAgent()
        self.product = ProductConsultantAgent()

    def run(self, user_input: str, trend_titles: list[str] | None = None) -> list[dict]:
        messages: list[AgentTrace | AgentFinal] = []
        decision = self.router.run(user_input)
        if not decision.in_scope:
            messages.append(
                self.router.trace(
                    "意图识别",
                    (
                        "我先判断这句话是否能进入电商运营工作流。当前没有识别到选品、流量、带货、平台策略或用户召回等业务目标，"
                        "所以先不继续分派给后续 Agent，避免给出偏题建议。"
                    ),
                )
            )
            messages.append(
                AgentFinal(
                    agent="TrendLogic",
                    content=(
                        "这个话题和 TrendLogic 的电商运营任务无关。TrendLogic 主要用于电商运营、选品分析、流量趋势和用户召回相关任务。"
                        "你可以向我描述你想做的商品、平台或目标用户，我会继续帮你分析。"
                    ),
                )
            )
            return [self._serialize(message) for message in messages]

        messages.append(
            self.router.trace(
                "意图识别",
                (
                    f"我先判断这是否属于 TrendLogic 的业务范围。当前问题和“{self._intent_label(decision.intent)}”有关，"
                    f"匹配度约为 {round(decision.confidence * 100)}%，可以进入需求补全流程。"
                ),
            )
        )
        profile = self.requirement.run(user_input)
        if not profile.is_complete_enough:
            messages.append(
                self.requirement.trace(
                    "需求补全",
                    (
                        "我开始整理你的需求画像，但现在还不能直接给选品结论。"
                        f"目前还缺少 {self._join_fields(profile.missing_fields)}，先补齐这些信息，后面的建议才会更贴近你的平台、预算和类目。"
                    ),
                )
            )
            messages.append(AgentFinal(agent="TrendLogic", content=self.requirement.follow_up(profile)))
            return [self._serialize(message) for message in messages]

        messages.append(
            self.requirement.trace(
                "需求结构化",
                (
                    f"我已经把你的需求整理成可执行的分析条件：平台是 {profile.target_platform}，类目是 {profile.target_category}，"
                    f"预算线索是 {profile.budget_range}。接下来可以进入选品建议。"
                ),
            )
        )
        messages.append(
            self.product.trace(
                "候选方向生成",
                (
                    f"我会把你的需求和当前公开爆品线索放在一起比较。"
                    f"{self._trend_hint(trend_titles)}然后先给出适合小规模测试的方向，而不是直接建议你大量备货。"
                ),
            )
        )
        messages.append(AgentFinal(agent="TrendLogic", content=self.product.run(profile, trend_titles)))
        return [self._serialize(message) for message in messages]

    @staticmethod
    def _serialize(message: AgentTrace | AgentFinal) -> dict:
        if isinstance(message, AgentTrace):
            data = asdict(message)
            data["type"] = "trace"
            return data
        return {"type": "final", "agent": message.agent, "content": message.content, "function": None}

    @staticmethod
    def _intent_label(intent: str) -> str:
        labels = {
            "product_selection": "选品咨询",
            "traffic_analysis": "流量趋势分析",
            "content_advice": "带货内容建议",
            "user_growth": "用户增长或召回",
            "platform_strategy": "平台策略",
        }
        return labels.get(intent, "电商运营")

    @staticmethod
    def _join_fields(fields: list[str]) -> str:
        if not fields:
            return "关键业务信息"
        if len(fields) == 1:
            return fields[0]
        return "、".join(fields)

    @staticmethod
    def _trend_hint(trend_titles: list[str] | None) -> str:
        if not trend_titles:
            return "当前还没有足够的公开爆品数据，"
        selected = "、".join(trend_titles[:3])
        return f"可参考的热点包括 {selected}，"
