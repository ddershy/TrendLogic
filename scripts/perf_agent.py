from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))

warnings.simplefilter("ignore")


PROMPTS = [
    "我想用5000元预算在小红书做二次元谷子店，目标学生党，低库存测试，帮我选品",
    "抖音上适合低成本测试的家居收纳类目有哪些，预算3000元，目标租房女生",
    "淘宝女包春夏上新，预算8000元，目标通勤白领，帮我判断优先方向",
    "小红书美妆新品按原价80%还是120%定价更合理，帮我拆测试方案",
    "最近宠物用品有什么适合内容种草的小爆品，预算5000元",
]


class FakeLLMClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.model = "fake-local-perf"

    @property
    def is_configured(self) -> bool:
        return True

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        system_text = messages[0].get("content", "") if messages else ""
        user_text = messages[-1].get("content", "") if messages else ""
        if "分类决策Agent" in system_text:
            return {
                "in_scope": True,
                "intent": "product_selection",
                "confidence": 0.91,
                "next_agent": "requirement_agent",
                "reason": "性能测试用本地判定结果。",
                "process_message": "我已判断这是电商运营相关问题，可以进入需求分析。",
            }
        if "需求分析 Agent" in system_text:
            return {
                "is_complete": True,
                "requirement_profile": {
                    "task_type": "product_selection",
                    "target_platform": _pick_platform(user_text),
                    "target_category": _pick_category(user_text),
                    "budget_range": 5000,
                    "target_audience": "预算敏感的内容平台用户",
                    "content_style": "图文种草",
                    "sales_goal": "低成本测试新品",
                    "risk_preference": "低库存",
                    "pricing_question": None,
                    "price_reference": None,
                    "known_constraints": ["先小流量测试"],
                },
                "missing_fields": [],
                "should_enter_consulting": True,
                "consulting_reason": "信息足够生成初版建议。",
                "follow_up_question": "",
                "process_message": "我已提取平台、类目、预算和目标用户，可以进入咨询建议。",
            }
        return {
            "process_message": "我会结合现有需求生成可执行建议。",
            "assumptions": ["先按轻库存、低预算、内容平台试错处理"],
            "recommendations": [
                {
                    "direction": "优先选择小体积、低客单、可成套销售的 SKU",
                    "reason": "便于用少量库存验证点击、收藏和成交，不把预算压在单品上",
                    "test_budget": "3-5 个 SKU，每个 SKU 小批量测试",
                    "risk_level": "中低",
                }
            ],
            "risk_notes": ["不要一开始重库存", "先验证内容转化再扩大采购"],
            "next_actions": ["拆 3 个内容角度", "记录点击、私信和成交数据"],
            "memory_candidates": [
                {
                    "candidate_type": "business_need",
                    "content": "用户希望低成本测试电商选品方向",
                    "tags": ["选品", "低库存"],
                }
            ],
        }

    def chat_with_tools(self, *_: Any, **__: Any) -> dict[str, Any]:
        return {"content": "", "messages": [], "tool_results": []}


def _pick_platform(text: str) -> str:
    for value in ["小红书", "抖音", "淘宝", "TikTok", "Amazon"]:
        if value in text:
            return value
    return "小红书"


def _pick_category(text: str) -> str:
    for value in ["二次元", "谷子", "家居收纳", "女包", "美妆", "宠物用品"]:
        if value in text:
            return value
    return "趋势品类"


def install_fake_llm() -> None:
    import agents.llm_client as llm_client
    import agents.product_consultant_agent as product_consultant_agent
    import agents.requirement_agent as requirement_agent
    import agents.router_agent as router_agent
    import agents.user_profile_agent as user_profile_agent

    llm_client.LLMClient = FakeLLMClient
    product_consultant_agent.LLMClient = FakeLLMClient
    requirement_agent.LLMClient = FakeLLMClient
    router_agent.LLMClient = FakeLLMClient
    user_profile_agent.LLMClient = FakeLLMClient
    product_consultant_agent.ProductConsultantAgent._query_rag_results = lambda self, user_input, profile: []


def setup_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trendlogic_backend.settings")
    import django

    django.setup()
    from django.conf import settings

    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * p))))
    return ordered[index]


def summarize(latencies: list[float], failures: int, total_wall_ms: float) -> dict[str, Any]:
    successes = len(latencies)
    return {
        "requests": successes + failures,
        "successes": successes,
        "failures": failures,
        "total_wall_ms": round(total_wall_ms, 3),
        "throughput_rps": round(successes / (total_wall_ms / 1000), 3) if total_wall_ms else 0,
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else 0,
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0,
            "p50": round(percentile(latencies, 0.50), 3),
            "p90": round(percentile(latencies, 0.90), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "max": round(max(latencies), 3) if latencies else 0,
        },
    }


def run_graph_once(index: int) -> float:
    from agents.graph import TrendLogicGraph

    prompt = PROMPTS[index % len(PROMPTS)]
    start = time.perf_counter()
    result = TrendLogicGraph().run(prompt, {})
    final_message = next((m for m in result.get("messages", []) if m.get("type") == "final"), None)
    if not final_message:
        raise RuntimeError("graph did not produce a final message")
    return (time.perf_counter() - start) * 1000


def run_api_once(index: int, token: str) -> float:
    from django.test import Client

    prompt = PROMPTS[index % len(PROMPTS)]
    client = Client()
    start = time.perf_counter()
    response = client.post(
        "/api/chat/message",
        data=json.dumps({"content": prompt}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    elapsed = (time.perf_counter() - start) * 1000
    if response.status_code != 200:
        raise RuntimeError(f"api status={response.status_code}, body={response.content[:300]!r}")
    return elapsed


def prepare_api_user() -> str:
    from django.test import Client

    client = Client()
    password = "perf-agent-123456"
    display_name = f"perf_{uuid.uuid4().hex[:10]}"
    response = client.post(
        "/api/auth/register",
        data=json.dumps(
            {
                "display_name": display_name,
                "password": password,
                "preferred_categories": ["二次元"],
                "preferred_platforms": ["小红书"],
            }
        ),
        content_type="application/json",
    )
    if response.status_code not in {200, 201}:
        raise RuntimeError(f"register status={response.status_code}, body={response.content[:300]!r}")
    return response.json()["access_token"]


def run_benchmark(target: str, requests: int, concurrency: int, warmup: int) -> dict[str, Any]:
    token = prepare_api_user() if target == "api" else ""
    worker = (lambda index: run_api_once(index, token)) if target == "api" else run_graph_once

    for index in range(warmup):
        worker(index)

    latencies: list[float] = []
    failures = 0
    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, index) for index in range(requests)]
        for future in as_completed(futures):
            try:
                latencies.append(future.result())
            except Exception as exc:
                failures += 1
                print(f"[failure] {exc}", file=sys.stderr)
    total_wall_ms = (time.perf_counter() - wall_start) * 1000
    return summarize(latencies, failures, total_wall_ms)


def main() -> int:
    parser = argparse.ArgumentParser(description="TrendLogic agent performance benchmark.")
    parser.add_argument("--target", choices=["graph", "api"], default="api")
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--real-llm", action="store_true", help="Use configured external LLM instead of local fake LLM.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "metrics" / "agent_perf_latest.json")
    args = parser.parse_args()

    if args.requests < 1:
        raise SystemExit("--requests must be >= 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    if args.warmup < 0:
        raise SystemExit("--warmup must be >= 0")

    if not args.real_llm:
        install_fake_llm()
    setup_django()

    result = {
        "target": args.target,
        "mode": "real_llm" if args.real_llm else "fake_llm",
        "requests": args.requests,
        "concurrency": args.concurrency,
        "warmup": args.warmup,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summary": run_benchmark(args.target, args.requests, args.concurrency, args.warmup),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["summary"]["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
