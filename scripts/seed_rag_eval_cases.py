from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trendlogic_backend.settings")


CASES = [
    {
        "name": "小红书爆品四要素",
        "query": "小红书爆品四要素是什么，选品时要满足哪些条件",
        "expected_filenames": ["xiaohongshu.md"],
        "expected_keywords": ["可视化效果", "情绪价值"],
    },
    {
        "name": "小红书测品达标标准",
        "query": "小红书小预算测品要看哪些数据，点击率互动率加购率标准是多少",
        "expected_filenames": ["xiaohongshu.md"],
        "expected_keywords": ["点击率", "加购率"],
    },
    {
        "name": "小红书五月应季节点品",
        "query": "小红书5月到6月适合上的端午毕业夏季节点品有哪些",
        "expected_filenames": ["xiaohongshu.md"],
        "expected_keywords": ["端午", "毕业季"],
    },
    {
        "name": "抖音爆品共性",
        "query": "抖音爆品有什么共性，客单价和内容形式怎么判断",
        "expected_filenames": ["tiktok.md"],
        "expected_keywords": ["强痛点", "客单友好"],
    },
    {
        "name": "抖音家居日用爆品",
        "query": "抖音家居日用高复购爆品有哪些，驱蚊收纳香薰适合吗",
        "expected_filenames": ["tiktok.md"],
        "expected_keywords": ["驱蚊喷雾", "桌面收纳"],
    },
    {
        "name": "抖音美妆个护爆品",
        "query": "抖音美妆个护里转化稳定的品有哪些，比如防晒和洗发水",
        "expected_filenames": ["tiktok.md"],
        "expected_keywords": ["去屑控油洗发水", "防晒喷雾"],
    },
    {
        "name": "泡芙账号定位",
        "query": "沃集鲜抹茶泡芙案例里账号人设和目标受众怎么定位",
        "expected_filenames": ["小红书泡芙运营案例.md"],
        "expected_keywords": ["超市零食挖宝酱", "18-35 岁女生"],
    },
    {
        "name": "泡芙七天内容排期",
        "query": "抹茶泡芙小红书7天内容排期怎么安排，首发测评场景合集分别做什么",
        "expected_filenames": ["小红书泡芙运营案例.md"],
        "expected_keywords": ["第 1 天", "第 7 天"],
    },
    {
        "name": "泡芙运营结果",
        "query": "沃集鲜抹茶泡芙运营结果怎么样，曝光赞藏评论和关键词效果是多少",
        "expected_filenames": ["小红书泡芙运营案例.md"],
        "expected_keywords": ["28 万", "2600"],
    },
    {
        "name": "泡芙购买答疑",
        "query": "沃集鲜抹茶泡芙多少钱一盒，保质期多久，在哪里买",
        "expected_filenames": ["小红书泡芙运营案例.md"],
        "expected_keywords": ["12.99", "短保"],
    },
]


def main() -> int:
    import django

    django.setup()
    from core.models import RAGEvaluationCase

    for item in CASES:
        defaults = {
            "query": item["query"],
            "category": "选品资料",
            "expected_document_ids": [],
            "expected_filenames": item["expected_filenames"],
            "expected_keywords": item["expected_keywords"],
            "top_k": 5,
            "is_active": True,
        }
        RAGEvaluationCase.objects.update_or_create(name=item["name"], defaults=defaults)
    print(f"seeded {len(CASES)} RAG evaluation cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
