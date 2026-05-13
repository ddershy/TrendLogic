from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator


def now_ms() -> float:
    return time.perf_counter() * 1000


@contextmanager
def measure_ms() -> Iterator[dict[str, float]]:
    start = now_ms()
    data = {"latency_ms": 0.0}
    try:
        yield data
    finally:
        data["latency_ms"] = round(now_ms() - start, 3)


def record_metric(
    event_type: str,
    latency_ms: float,
    route: str = "",
    user: Any | None = None,
    session: Any | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        from core.models import MetricEvent
    except Exception:
        return
    try:
        MetricEvent.objects.create(
            event_type=event_type,
            route=route,
            user=user,
            session=session,
            latency_ms=round(float(latency_ms or 0.0), 3),
            metadata=metadata or {},
        )
    except Exception:
        return
