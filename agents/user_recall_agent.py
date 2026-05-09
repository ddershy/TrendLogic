from __future__ import annotations

from .base_agent import BaseAgent


class RecallAgent(BaseAgent):
    name = "用户召回Agent"

    def generate(self, display_name: str, categories: list[str], trends: list[str], score: float) -> dict:
        category = categories[0] if categories else "你关注的方向"
        trend = trends[0] if trends else "近期热门选品"
        return {
            "recall_score": round(score, 2),
            "matched_trends": trends[:3],
            "reason": f"用户历史偏好与 {trend} 存在匹配，可尝试召回。",
            "message": (
                f"{display_name}，最近“{trend}”相关热度在上升，和你之前关注的“{category}”方向比较接近。"
                "我们已经整理了一批增长较快的细分类目和内容切入角度，可以回来看看有没有适合测试的新品方向。"
            ),
        }
