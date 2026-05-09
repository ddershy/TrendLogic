from __future__ import annotations

from .base_agent import BaseAgent


class UserProfileAgent(BaseAgent):
    name = "用户画像Agent"

    def extract_tags(self, text: str) -> list[str]:
        tags = []
        for keyword in ["小红书", "抖音", "美妆", "女包", "收纳", "数码", "低成本", "低风险", "短视频"]:
            if keyword in text:
                tags.append(keyword)
        return tags
