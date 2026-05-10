from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ChatMessage,
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
    list_display = ("title", "user", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "user__display_name", "user__account_id")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("short_content", "session", "user", "role", "message_type", "agent_name", "created_at")
    list_filter = ("role", "message_type", "agent_name", "created_at")
    search_fields = ("content", "user__display_name", "session__title", "agent_name")
    readonly_fields = ("id", "created_at")

    @admin.display(description="内容")
    def short_content(self, obj: ChatMessage) -> str:
        return obj.content[:48] + ("..." if len(obj.content) > 48 else "")


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
    list_display = ("title", "user", "memory_type", "memory_scope", "status", "importance", "confidence", "decay_score", "last_used_at")
    list_filter = ("memory_type", "memory_scope", "status", "source", "last_used_at", "created_at")
    search_fields = ("title", "content", "summary", "tags", "user__display_name", "user__account_id", "session__title")
    readonly_fields = ("id", "created_at", "updated_at")
    list_editable = ("status", "importance", "confidence", "decay_score")
    fieldsets = (
        ("归属", {"fields": ("id", "user", "session")}),
        ("分类", {"fields": ("memory_type", "memory_scope", "status", "source")}),
        ("内容", {"fields": ("title", "content", "summary", "tags")}),
        ("评分", {"fields": ("importance", "confidence", "decay_score", "last_used_at")}),
        ("时间", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="摘要")
    def short_summary(self, obj: UserMemory) -> str:
        return obj.summary[:64] + ("..." if len(obj.summary) > 64 else "")


@admin.register(RecallRecord)
class RecallRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "recall_score", "created_by", "created_at", "short_message")
    list_filter = ("created_at", "recall_score")
    search_fields = ("generated_message", "user__display_name", "created_by__display_name", "matched_trends")
    readonly_fields = ("id", "created_at")

    @admin.display(description="召回文案")
    def short_message(self, obj: RecallRecord) -> str:
        return obj.generated_message[:64] + ("..." if len(obj.generated_message) > 64 else "")
