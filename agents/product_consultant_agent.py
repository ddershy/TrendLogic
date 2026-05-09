from __future__ import annotations

from .base_agent import BaseAgent
from .requirement_agent import RequirementProfile


class ProductConsultantAgent(BaseAgent):
    name = "选品咨询Agent"

    def run(self, profile: RequirementProfile, trend_titles: list[str] | None = None) -> str:
        platform = profile.target_platform or "目标平台"
        category = profile.target_category or "相关类目"
        trends = trend_titles or ["轻量化收纳", "低成本内容种草", "高展示性小商品"]
        return (
            f"基于你当前的需求，我建议先围绕“{category}”做小批量测试，优先选择适合在 {platform} 展示的轻库存商品。\n\n"
            f"可以先测试 3 个方向：\n"
            f"1. 与“{trends[0]}”相关的高展示性单品；\n"
            f"2. 客单价适中、内容素材容易拍摄的组合套装；\n"
            f"3. 能和近期热点“{trends[-1]}”结合的细分类目。\n\n"
            "起步建议：先用 3-5 条内容验证点击和收藏，再决定是否补货；如果数据不错，再进入供应链比价和达人素材测试。"
        )
