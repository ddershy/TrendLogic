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
