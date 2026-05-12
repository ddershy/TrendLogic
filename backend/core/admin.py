from __future__ import annotations

from django.contrib import admin
from django.db import connection
from django.utils.html import format_html

from .models import (
    ChatSession,
    RecallRecord,
    TrendingCategory,
    TrendingItem,
    UploadedDocument,
    User,
    UserMemory,
    UserProfile,
)

admin.site.site_header = "TrendLogic 管理后台"
admin.site.site_title = "TrendLogic Admin"
admin.site.index_title = "运营数据管理"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("display_name", "account_id", "role", "created_at", "updated_at")
    list_filter = ("role", "created_at")
    search_fields = ("display_name", "account_id")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("基础信息", {"fields": ("id", "account_id", "display_name", "role", "password_hash")}),
        ("偏好", {"fields": ("preferences",)}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "recall_score", "interaction_frequency", "last_active_at", "updated_at")
    list_filter = ("last_active_at", "updated_at")
    search_fields = ("user__display_name", "user__account_id", "summary")
    readonly_fields = ("id", "updated_at")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "message_count", "last_message_at", "created_at", "updated_at")
    list_filter = ("last_message_at", "created_at", "updated_at")
    search_fields = ("title", "user_transcript", "assistant_transcript", "session_summary", "user__display_name", "user__account_id")
    readonly_fields = ("id", "message_count", "last_message_at", "created_at", "updated_at")
    fieldsets = (
        ("归属", {"fields": ("id", "user", "title")}),
        ("会话文本", {"fields": ("user_transcript", "assistant_transcript", "recent_interactions")}),
        ("摘要", {"fields": ("session_summary", "trace_summary")}),
        ("计数", {"fields": ("message_count", "last_message_at")}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )

    def delete_model(self, request, obj):
        cleanup_legacy_chat_session_references([obj.id])
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        cleanup_legacy_chat_session_references(list(queryset.values_list("id", flat=True)))
        super().delete_queryset(request, queryset)


@admin.register(TrendingCategory)
class TrendingCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "description", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    list_editable = ("is_active", "sort_order")
    readonly_fields = ("id", "created_at")


@admin.register(TrendingItem)
class TrendingItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "heat_badge", "visibility", "is_ai_generated", "created_by", "created_at")
    list_filter = ("category", "visibility", "is_ai_generated", "created_at")
    search_fields = ("title", "summary", "tags", "created_by__display_name")
    list_editable = ("visibility", "is_ai_generated")
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="热度")
    def heat_badge(self, obj: TrendingItem) -> str:
        score = round(obj.heat_score * 100)
        return format_html("<strong>{} 分</strong>", score)


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "category", "visibility", "vectorized", "uploaded_by", "created_at")
    list_filter = ("category", "visibility", "vectorized", "created_at")
    search_fields = ("filename", "file_path", "uploaded_by__display_name")
    list_editable = ("vectorized",)
    readonly_fields = ("id", "created_at")


@admin.register(UserMemory)
class UserMemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "confidence", "last_used_at", "updated_at")
    list_filter = ("last_used_at", "created_at", "updated_at")
    search_fields = ("user__display_name", "user__account_id", "short_term_summary", "long_term_summary", "tags")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("归属", {"fields": ("id", "user")}),
        ("记忆摘要", {"fields": ("short_term_summary", "long_term_summary")}),
        ("偏好与需求", {"fields": ("preferences", "negative_preferences", "business_needs", "behavior_notes", "recall_signals", "tags")}),
        ("状态", {"fields": ("confidence", "last_used_at")}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(RecallRecord)
class RecallRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "recall_score", "created_by", "created_at", "short_message")
    list_filter = ("created_at", "recall_score")
    search_fields = ("generated_message", "user__display_name", "created_by__display_name", "matched_trends")
    readonly_fields = ("id", "created_at")

    @admin.display(description="召回文案")
    def short_message(self, obj: RecallRecord) -> str:
        return obj.generated_message[:64] + ("..." if len(obj.generated_message) > 64 else "")


def cleanup_legacy_chat_session_references(session_ids: list[str]) -> None:
    if not session_ids:
        return
    existing_tables = set(connection.introspection.table_names())
    legacy_tables = [
        ("core_chatmessage", "session_id"),
        ("user_memories", "session_id"),
    ]
    placeholders = ", ".join(["%s"] * len(session_ids))
    with connection.cursor() as cursor:
        for table_name, column_name in legacy_tables:
            if table_name in existing_tables:
                cursor.execute(f"DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})", session_ids)
