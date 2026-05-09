from __future__ import annotations

from dataclasses import dataclass, field

from .base_agent import BaseAgent


@dataclass
class RequirementProfile:
    target_platform: str | None = None
    target_category: str | None = None
    budget_range: str | None = None
    target_audience: str | None = None
    content_style: str | None = None
    sales_goal: str | None = None
    risk_preference: str | None = None
    known_constraints: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)

    @property
    def is_complete_enough(self) -> bool:
        return self.target_platform is not None and self.target_category is not None and self.budget_range is not None


class RequirementAgent(BaseAgent):
    name = "需求分析Agent"

    PLATFORMS = ["小红书", "抖音", "淘宝", "TikTok", "Amazon", "亚马逊", "拼多多", "快手"]
    CATEGORIES = ["美妆", "女包", "收纳", "数码", "母婴", "宠物", "服饰", "食品", "家居", "户外"]

    def run(self, user_input: str) -> RequirementProfile:
        profile = RequirementProfile()
        for platform in self.PLATFORMS:
            if platform.lower() in user_input.lower():
                profile.target_platform = platform
                break
        for category in self.CATEGORIES:
            if category in user_input:
                profile.target_category = category
                break
        if any(word in user_input for word in ["低成本", "轻资产", "不压库存", "低风险"]):
            profile.risk_preference = "低风险"
            profile.known_constraints.append("希望低库存或轻资产试错")
        if any(word in user_input for word in ["种草", "笔记"]):
            profile.content_style = "种草型"
        if any(word in user_input for word in ["短视频", "直播"]):
            profile.content_style = "短视频带货"
        profile.budget_range = self._extract_budget(user_input)
        missing = []
        if not profile.target_platform:
            missing.append("目标平台")
        if not profile.target_category:
            missing.append("目标类目")
        if not profile.budget_range:
            missing.append("预算区间")
        profile.missing_fields = missing
        return profile

    def follow_up(self, profile: RequirementProfile) -> str:
        questions = {
            "目标平台": "你主要想在哪个平台销售或做内容，比如小红书、抖音、淘宝还是 TikTok？",
            "目标类目": "你目前更关注哪个类目，比如美妆、女包、收纳、数码或家居？",
            "预算区间": "这次测试预算大概是多少，比如 3000 元以内、5000-10000 元，还是更高？",
        }
        selected = [questions[field] for field in profile.missing_fields[:3]]
        return "为了更准确地帮你分析，我需要先确认：" + " ".join(selected)

    @staticmethod
    def _extract_budget(text: str) -> str | None:
        budget_markers = ["预算", "元", "块", "w", "万"]
        if any(marker in text for marker in budget_markers):
            return "用户已提及预算，需在后续对话中精确确认"
        return None
