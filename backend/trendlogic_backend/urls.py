from __future__ import annotations

from django.urls import path

from core import views

urlpatterns = [
    path("health", views.health),
    path("api/auth/register", views.register),
    path("api/auth/login", views.login),
    path("api/auth/me", views.me),
    path("api/chat/message", views.chat_message),
    path("api/chat/sessions", views.chat_sessions),
    path("api/chat/session", views.create_chat_session),
    path("api/chat/history", views.chat_history),
    path("api/trending", views.trending_collection),
    path("api/trending/categories", views.trending_categories),
    path("api/trending/<str:item_id>", views.trending_detail),
    path("api/admin/users", views.admin_users),
    path("api/admin/user-insights", views.user_insights),
    path("api/admin/rag/upload", views.rag_upload),
    path("api/admin/rag/documents", views.rag_documents),
    path("api/recall/candidates", views.recall_candidates),
    path("api/recall/generate", views.recall_generate),
    path("api/users/<str:user_id>/memory", views.user_memory),
    path("api/users/<str:user_id>/memory/summarize", views.summarize_memory),
]
