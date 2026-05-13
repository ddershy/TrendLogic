from __future__ import annotations


def summarize_trends(items: list[dict]) -> list[str]:
    return [str(item.get("title", "")) for item in items if item.get("title")]


def query_trending_items_tool(
    category: str = "",
    keyword: str = "",
    tags: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """Query public trending items from the Django database."""

    try:
        from core.models import TrendingItem
    except Exception:
        return []

    queryset = TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at")
    if category:
        queryset = queryset.filter(category__icontains=category)
    if keyword:
        from django.db.models import Q

        queryset = queryset.filter(Q(title__icontains=keyword) | Q(summary__icontains=keyword))

    result = []
    tag_values = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
    for item in queryset[: max(int(limit or 5) * 3, 5)]:
        item_tags = [str(tag) for tag in (item.tags or [])]
        if tag_values and not any(tag in item_tags for tag in tag_values):
            continue
        result.append(
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "summary": item.summary,
                "tags": item.tags,
                "heat_score": item.heat_score,
            }
        )
        if len(result) >= int(limit or 5):
            break
    return result


def query_trending_categories_tool(active_only: bool = True) -> list[dict]:
    """Query trending categories from the Django database."""

    try:
        from core.models import TrendingCategory
    except Exception:
        return []

    queryset = TrendingCategory.objects.order_by("sort_order", "name")
    if active_only:
        queryset = queryset.filter(is_active=True)
    return [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "is_active": item.is_active,
            "sort_order": item.sort_order,
        }
        for item in queryset
    ]


def query_trending_stats_tool(limit: int = 10) -> dict:
    """Return lightweight category and tag stats for public trending items."""

    try:
        from core.models import TrendingItem
    except Exception:
        return {"category_counts": {}, "top_tags": []}

    category_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    for item in TrendingItem.objects.filter(visibility="public"):
        category_counts[item.category] = category_counts.get(item.category, 0) + 1
        for tag in item.tags or []:
            label = str(tag).strip()
            if label:
                tag_counts[label] = tag_counts.get(label, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda pair: pair[1], reverse=True)[: int(limit or 10)]
    return {
        "category_counts": category_counts,
        "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
    }
