from __future__ import annotations

import uuid

from django.db import models


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class User(models.Model):
    ROLE_CHOICES = [("normal_user", "Normal User"), ("admin", "Admin")]

    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("u"))
    account_id = models.CharField(max_length=32, unique=True, db_index=True)
    display_name = models.CharField(max_length=80, unique=True, db_index=True)
    password_hash = models.CharField(max_length=256)
    role = models.CharField(max_length=24, choices=ROLE_CHOICES, default="normal_user")
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatSession(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("s"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=160, default="新的运营咨询")
    user_transcript = models.TextField(default="", blank=True)
    assistant_transcript = models.TextField(default="", blank=True)
    session_summary = models.TextField(default="", blank=True)
    trace_summary = models.TextField(default="", blank=True)
    recent_interactions = models.JSONField(default=list, blank=True)
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TrendingCategory(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("tc"))
    name = models.CharField(max_length=80, unique=True, db_index=True)
    description = models.CharField(max_length=240, default="", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)


class TrendingItem(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("t"))
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=80)
    source = models.CharField(max_length=120, default="user_upload")
    summary = models.TextField()
    heat_score = models.FloatField(default=0.5)
    tags = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    visibility = models.CharField(max_length=32, default="public")
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UploadedDocument(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("doc"))
    filename = models.CharField(max_length=240)
    file_path = models.CharField(max_length=500)
    category = models.CharField(max_length=80, default="选品资料")
    visibility = models.CharField(max_length=32, default="private_rag_only")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    vectorized = models.BooleanField(default=False)
    chunk_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class UserProfile(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("p"))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    summary = models.TextField(default="", blank=True)
    interest_weights = models.JSONField(default=dict, blank=True)
    negative_preferences = models.JSONField(default=list, blank=True)
    preferred_platforms = models.JSONField(default=list, blank=True)
    preferred_categories = models.JSONField(default=list, blank=True)
    recall_score = models.FloatField(default=0.0)
    interaction_frequency = models.IntegerField(default=0)
    last_active_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class UserMemory(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("mem"))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="memory")
    short_messages = models.JSONField(default=dict, blank=True)
    short_term_summary = models.TextField(default="", blank=True)
    long_term_summary = models.TextField(default="", blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    negative_preferences = models.JSONField(default=list, blank=True)
    business_needs = models.JSONField(default=list, blank=True)
    behavior_notes = models.JSONField(default=list, blank=True)
    recall_signals = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.7)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_memory_profiles"
        indexes = [models.Index(fields=["last_used_at"])]


class RecallRecord(models.Model):
    id = models.CharField(primary_key=True, max_length=32, default=lambda: new_id("r"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recall_records")
    recall_score = models.FloatField(default=0.0)
    matched_trends = models.JSONField(default=list, blank=True)
    generated_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_recall_records")
