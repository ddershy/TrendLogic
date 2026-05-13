from __future__ import annotations

import json
import secrets
import time
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import connection
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from agents.graph import TrendLogicGraph
from agents.user_profile_agent import UserProfileAgent
from agents.user_recall_agent import RecallAgent
from memory.service import MemoryService

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

signer = TimestampSigner()


def health(_: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "service": "TrendLogic"})


@csrf_exempt
def register(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    display_name = str(payload.get("display_name", "")).strip()
    password = str(payload.get("password", ""))
    if len(display_name) < 2 or len(password) < 6:
        return error("名字至少 2 个字符，密码至少 6 位", 400)
    if User.objects.filter(display_name=display_name).exists():
        return error("Display name already exists", 409)

    preferred_categories = ensure_list(payload.get("preferred_categories"))
    preferred_platforms = ensure_list(payload.get("preferred_platforms"))
    role = "admin" if payload.get("admin_invite_code") == settings.ADMIN_INVITE_CODE else "normal_user"
    user = User.objects.create(
        account_id=generate_account_id(),
        display_name=display_name,
        password_hash=password,
        role=role,
        preferences={
            "preferred_categories": preferred_categories,
            "preferred_platforms": preferred_platforms,
            "business_focus": payload.get("business_focus"),
        },
    )
    UserProfile.objects.create(
        user=user,
        summary="新用户，等待更多对话形成长期偏好。",
        preferred_categories=preferred_categories,
        preferred_platforms=preferred_platforms,
        interest_weights={tag: 0.45 for tag in preferred_categories + preferred_platforms},
    )
    if preferred_categories or preferred_platforms or payload.get("business_focus"):
        memory = MemoryService().get_or_create_memory(user)
        memory.preferences = user.preferences
        memory.tags = sorted(set(preferred_categories + preferred_platforms))
        memory.confidence = 0.8
        memory.last_used_at = timezone.now()
        memory.save(update_fields=["preferences", "tags", "confidence", "last_used_at", "updated_at"])
    return JsonResponse(auth_response(user))


@csrf_exempt
def login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    identifier = str(payload.get("identifier", "")).strip()
    password = str(payload.get("password", ""))
    user = User.objects.filter(Q(account_id=identifier) | Q(display_name=identifier)).first()
    if not user or not verify_password(password, user.password_hash):
        return error("Invalid account or password", 401)
    return JsonResponse(auth_response(user))


def me(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    return JsonResponse(serialize_user(user))


@csrf_exempt
def chat_message(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    content, session_or_response = prepare_chat_turn(user, payload)
    if isinstance(session_or_response, JsonResponse):
        return session_or_response
    try:
        response = run_chat_graph(user, session_or_response, content)
    except Exception as exc:
        return error(f"Agent 执行失败：{exc}", 500)
    return JsonResponse(response)


@csrf_exempt
def chat_message_stream(request: HttpRequest) -> JsonResponse | StreamingHttpResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    content, session_or_response = prepare_chat_turn(user, payload)
    if isinstance(session_or_response, JsonResponse):
        return session_or_response
    session = session_or_response

    def event_stream():
        yield stream_event("session", {"session_id": session.id})
        yield stream_event(
            "process",
            {
                "message": {
                    "type": "process",
                    "agent": "系统",
                    "function": "接收请求",
                    "content": "我已经收到你的问题，正在读取用户记忆并进入 Agent 流程。",
                }
            },
        )
        memory_service = MemoryService()
        memory_context = memory_service.load_context(user, session)
        final_state = {
            "messages": [],
            "memory_candidates": [],
        }
        final_message = ""
        trace_messages = []
        try:
            for step in TrendLogicGraph().run_steps(content, memory_context.to_dict()):
                if step.get("state"):
                    final_state = step["state"]
                for message in step.get("new_messages", []):
                    if message.get("type") == "process":
                        yield stream_event("process", {"message": message})
                        if not step.get("ephemeral"):
                            trace_messages.append(message)
                    elif message.get("type") == "final":
                        final_message = str(message.get("content") or "")
        except Exception as exc:
            error_message = f"Agent 执行失败：{exc}"
            process_message = {
                "type": "process",
                "agent": "系统",
                "function": "错误定位",
                "content": error_message,
            }
            yield stream_event("process", {"message": process_message})
            trace_messages.append(process_message)
            final_message = error_message
        memory_service.record_interaction(
            user=user,
            session=session,
            user_message=content,
            assistant_message=final_message,
            trace_messages=trace_messages,
            memory_candidates=final_state.get("memory_candidates", []),
        )
        yield stream_event("final_start", {"message": {"type": "final", "agent": "TrendLogic", "content": ""}})
        for chunk in chunk_text(final_message):
            yield stream_event("final_delta", {"content": chunk})
            time.sleep(0.012)
        yield stream_event("done", {"session_id": session.id})

    return StreamingHttpResponse(event_stream(), content_type="application/x-ndjson; charset=utf-8")


def chat_sessions(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    sessions = ChatSession.objects.filter(user=user).order_by("-updated_at")
    return JsonResponse([serialize_session(session) for session in sessions], safe=False)


@csrf_exempt
def create_chat_session(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if request.method != "POST":
        return method_not_allowed()
    return JsonResponse(serialize_session(ChatSession.objects.create(user=user)))


@csrf_exempt
def chat_session_detail(request: HttpRequest, session_id: str) -> JsonResponse | HttpResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    session = ChatSession.objects.filter(id=session_id, user=user).first()
    if not session:
        return error("Session not found", 404)
    if request.method == "DELETE":
        cleanup_legacy_chat_session_references([session.id])
        session.delete()
        return HttpResponse(status=204)
    return method_not_allowed()


def chat_history(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    session = ChatSession.objects.filter(id=request.GET.get("session_id"), user=user).first()
    if not session:
        return error("Session not found", 404)
    return JsonResponse(serialize_session_detail(session))


def memory_context(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    session = None
    session_id = request.GET.get("session_id")
    if session_id:
        session = ChatSession.objects.filter(id=session_id, user=user).first()
        if not session:
            return error("Session not found", 404)
    context = MemoryService().load_context(user, session)
    return JsonResponse({"memory_context": context.to_dict()})


@csrf_exempt
def session_memory_update(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    session = ChatSession.objects.filter(id=payload.get("session_id"), user=user).first()
    if not session:
        return error("Session not found", 404)
    memory_service = MemoryService()
    plan = memory_service.update_long_term(user=user, session=session)
    memory = memory_service.get_or_create_memory(user)
    return JsonResponse(
        {
            "status": "ok",
            "memory": serialize_memory(memory),
            "memory_context": memory_service.load_context(user, session).to_dict(),
            "update_plan": plan.to_dict(),
        }
    )


@csrf_exempt
def trending_collection(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if request.method == "GET":
        items = TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at")
        return JsonResponse([serialize_trending_item(item) for item in items], safe=False)
    if request.method == "POST":
        payload = read_json(request)
        if payload.get("visibility") == "private_rag_only" and user.role != "admin":
            return error("Only admin can create private RAG items", 403)
        item = TrendingItem.objects.create(
            title=str(payload.get("title", "")).strip(),
            category=str(payload.get("category", "")).strip(),
            summary=str(payload.get("summary", "")).strip(),
            source=str(payload.get("source", "user_upload")),
            heat_score=float(payload.get("heat_score", 0.5)),
            tags=ensure_list(payload.get("tags")),
            visibility=str(payload.get("visibility", "public")),
            is_ai_generated=bool(payload.get("is_ai_generated", False)),
            created_by=user,
        )
        return JsonResponse(serialize_trending_item(item), status=201)
    return method_not_allowed()


def trending_categories(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    seed_default_categories()
    categories = TrendingCategory.objects.filter(is_active=True).order_by("sort_order", "name").values_list("name", flat=True)
    return JsonResponse(list(categories), safe=False)


@csrf_exempt
def trending_detail(request: HttpRequest, item_id: str) -> JsonResponse | HttpResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    item = TrendingItem.objects.filter(id=item_id).first()
    if not item:
        return error("Trending item not found", 404)
    if user.role != "admin" and item.created_by_id != user.id:
        return error("Cannot edit this item", 403)
    if request.method == "PUT":
        payload = read_json(request)
        if payload.get("visibility") == "private_rag_only" and user.role != "admin":
            return error("Only admin can mark private RAG items", 403)
        for field in ["title", "category", "summary", "source", "heat_score", "tags", "visibility", "is_ai_generated"]:
            if field in payload:
                setattr(item, field, payload[field])
        item.save()
        return JsonResponse(serialize_trending_item(item))
    if request.method == "DELETE":
        item.delete()
        return HttpResponse(status=204)
    return method_not_allowed()


def admin_users(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    users = User.objects.order_by("-created_at")
    return JsonResponse(
        [
            {
                "id": user.id,
                "account_id": user.account_id,
                "display_name": user.display_name,
                "role": user.role,
                "created_at": iso(user.created_at),
            }
            for user in users
        ],
        safe=False,
    )


def user_insights(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    rows = []
    for user in User.objects.order_by("-created_at"):
        profile = getattr(user, "profile", None)
        rows.append(serialize_user_insight(user, profile))
    return JsonResponse(rows, safe=False)


@csrf_exempt
def rag_upload(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    if request.method != "POST":
        return method_not_allowed()
    uploaded = request.FILES.get("file")
    if not uploaded:
        return error("File is required", 400)
    upload_dir = Path(settings.BASE_DIR / "uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target = upload_dir / f"{admin.id}_{uploaded.name}"
    with target.open("wb") as buffer:
        for chunk in uploaded.chunks():
            buffer.write(chunk)
    document = UploadedDocument.objects.create(
        filename=uploaded.name,
        file_path=str(target),
        category=request.POST.get("category", "选品资料"),
        uploaded_by=admin,
    )
    return JsonResponse(serialize_document(document), status=201)


def rag_documents(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    documents = UploadedDocument.objects.order_by("-created_at")
    return JsonResponse([serialize_document(document) for document in documents], safe=False)


def recall_candidates(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    result = []
    recall_agent = RecallAgent()
    memory_service = MemoryService()
    trends = [serialize_trend_for_agent(item) for item in TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at")[:12]]
    for user in User.objects.exclude(role="admin"):
        profile = getattr(user, "profile", None)
        memory = memory_service.get_or_create_memory(user)
        assessment = recall_agent.assess_candidate(
            user={
                **serialize_user(user),
                "last_active_at": iso(profile.last_active_at) if profile and profile.last_active_at else None,
            },
            profile=serialize_profile_for_agent(user, profile),
            memory=serialize_memory(memory),
            trends=trends,
        )
        result.append(assessment.to_dict())
    return JsonResponse(sorted(result, key=lambda item: item["recall_score"], reverse=True), safe=False)


@csrf_exempt
def recall_generate(request: HttpRequest) -> JsonResponse:
    admin = require_admin(request)
    if isinstance(admin, JsonResponse):
        return admin
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    user = User.objects.filter(id=payload.get("user_id")).first()
    if not user:
        return error("User not found", 404)
    profile = getattr(user, "profile", None)
    memory_service = MemoryService()
    memory = memory_service.get_or_create_memory(user)
    trend_items = [serialize_trend_for_agent(item) for item in TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at")[:12]]
    assessment = RecallAgent().assess_candidate(
        user={
            **serialize_user(user),
            "last_active_at": iso(profile.last_active_at) if profile and profile.last_active_at else None,
        },
        profile=serialize_profile_for_agent(user, profile),
        memory=serialize_memory(memory),
        trends=trend_items,
    )
    generated = RecallAgent().generate(
        user.display_name,
        assessment.preferred_categories,
        assessment.matched_trends,
        assessment.recall_score,
        profile=serialize_profile_for_agent(user, profile),
        memory=serialize_memory(memory),
        trending_items=trend_items,
    )
    RecallRecord.objects.create(
        user=user,
        recall_score=generated["recall_score"],
        matched_trends=generated["matched_trends"],
        generated_message=generated["message"],
        created_by=admin,
    )
    memory_service.append_memory_list(
        user=user,
        field_name="recall_signals",
        item={
            "message": generated["message"],
            "reason": generated["reason"],
            "matched_trends": generated["matched_trends"],
            "recall_score": generated["recall_score"],
            "recommended_channel": generated.get("recommended_channel", ""),
            "timing": generated.get("timing", ""),
            "created_at": iso(timezone.now()),
        },
    )
    return JsonResponse({"user_id": user.id, **generated})


@csrf_exempt
def user_memory(request: HttpRequest, user_id: str) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if user.role != "admin" and user.id != user_id:
        return error("Cannot access this memory", 403)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return error("User not found", 404)
    memory_service = MemoryService()
    memory = memory_service.get_or_create_memory(target)
    if request.method == "GET":
        return JsonResponse({"user_id": user_id, "memory": serialize_memory(memory)})
    if request.method == "PUT":
        payload = read_json(request)
        memory_service.update_memory_from_payload(memory, payload)
        return JsonResponse({"user_id": user_id, "memory": serialize_memory(memory)})
    return method_not_allowed()


def user_workspace(request: HttpRequest, user_id: str) -> JsonResponse:
    requester = current_user(request)
    if not requester:
        return error("Invalid or expired token", 401)
    if requester.role != "admin" and requester.id != user_id:
        return error("Cannot access this workspace", 403)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return error("User not found", 404)

    profile = getattr(target, "profile", None)
    recent_sessions = ChatSession.objects.filter(user=target).order_by("-updated_at")[:10]
    recall_records = RecallRecord.objects.filter(user=target).order_by("-created_at")[:20]
    return JsonResponse(
        {
            "user": serialize_user(target),
            "profile": serialize_user_insight(target, profile),
            "recent_sessions": [serialize_session(session) for session in recent_sessions],
            "recent_conversations": [serialize_session_detail(session) for session in recent_sessions],
            "memory": serialize_memory(MemoryService().get_or_create_memory(target)),
            "recall_records": [serialize_recall_record(record) for record in recall_records],
        }
    )


@csrf_exempt
def summarize_memory(request: HttpRequest, user_id: str) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if user.role != "admin" and user.id != user_id:
        return error("Cannot summarize this memory", 403)
    target = User.objects.filter(id=user_id).first()
    if not target:
        return error("User not found", 404)
    memory_service = MemoryService()
    recent_sessions = list(ChatSession.objects.filter(user=target).order_by("-updated_at")[:8])
    context = memory_service.load_context(target, recent_sessions[0] if recent_sessions else None)
    plan = UserProfileAgent().analyze(
        user=serialize_user(target),
        memory_context=context.to_dict(),
        recent_sessions=[serialize_session_detail(session) for session in recent_sessions],
    )
    apply_profile_update_plan(target, plan)
    memory = memory_service.get_or_create_memory(target)
    return JsonResponse({"status": "ok", "memory": serialize_memory(memory), "profile_update_plan": plan.to_dict()})


def apply_profile_update_plan(user: User, plan) -> None:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    memory = MemoryService().get_or_create_memory(user)

    if plan.profile_summary:
        profile.summary = plan.profile_summary
    if plan.preferred_categories:
        profile.preferred_categories = merge_unique(profile.preferred_categories, plan.preferred_categories)
    if plan.preferred_platforms:
        profile.preferred_platforms = merge_unique(profile.preferred_platforms, plan.preferred_platforms)
    if plan.negative_preferences:
        profile.negative_preferences = merge_unique(profile.negative_preferences, plan.negative_preferences)
    if plan.interest_weights:
        profile.interest_weights = merge_weights(profile.interest_weights, plan.interest_weights)
    profile.recall_score = max(float(profile.recall_score or 0), float(plan.recall_score or 0))
    profile.last_active_at = profile.last_active_at or timezone.now()
    profile.save()

    if plan.long_term_summary:
        memory.long_term_summary = plan.long_term_summary
    memory.preferences = merge_memory_preferences(memory.preferences, [*plan.preferred_categories, *plan.preferred_platforms])
    memory.negative_preferences = merge_unique(memory.negative_preferences, plan.negative_preferences)
    memory.business_needs = merge_unique(memory.business_needs, plan.business_needs)
    memory.behavior_notes = merge_unique(memory.behavior_notes, plan.behavior_notes)
    memory.tags = merge_unique(memory.tags, plan.tags)
    memory.confidence = max(float(memory.confidence or 0), float(plan.confidence or 0))
    memory.last_used_at = timezone.now()
    memory.save()


def prepare_chat_turn(user: User, payload: dict) -> tuple[str, ChatSession | JsonResponse]:
    content = str(payload.get("content", "")).strip()
    if not content:
        return "", error("Message cannot be empty", 400)
    return content, get_or_create_session(user, payload.get("session_id"), content)


def run_chat_graph(user: User, session: ChatSession, content: str) -> dict:
    memory_service = MemoryService()
    memory_context = memory_service.load_context(user, session)
    result = TrendLogicGraph().run(content, memory_context.to_dict())
    messages = result["messages"]
    final_message = next((message["content"] for message in reversed(messages) if message.get("type") == "final"), "")
    trace_messages = [message for message in messages if message.get("type") == "process"]
    memory_service.record_interaction(
        user=user,
        session=session,
        user_message=content,
        assistant_message=final_message,
        trace_messages=trace_messages,
        memory_candidates=result.get("memory_candidates", []),
    )
    return {"session_id": session.id, "messages": messages}


def stream_event(event: str, data: dict) -> str:
    return json.dumps({"event": event, **data}, ensure_ascii=False) + "\n"


def chunk_text(text: str, size: int = 6):
    for index in range(0, len(text), size):
        yield text[index : index + size]


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


def read_json(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def auth_response(user: User) -> dict:
    return {"access_token": signer.sign(user.id), "token_type": "bearer", "user": serialize_user(user)}


def verify_password(raw_password: str, stored_password: str) -> bool:
    if raw_password == stored_password:
        return True
    try:
        return check_password(raw_password, stored_password)
    except Exception:
        return False


def current_user(request: HttpRequest) -> User | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ").strip()
    try:
        user_id = signer.unsign(token, max_age=settings.TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    return User.objects.filter(id=user_id).first()


def require_admin(request: HttpRequest) -> User | JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if user.role != "admin":
        return error("Admin permission required", 403)
    return user


def generate_account_id() -> str:
    for _ in range(20):
        account_id = f"TL{timezone.now():%Y%m%d}{secrets.randbelow(10000):04d}"
        if not User.objects.filter(account_id=account_id).exists():
            return account_id
    raise RuntimeError("Failed to generate account id")


def get_or_create_session(user: User, session_id: str | None, first_message: str) -> ChatSession:
    if session_id:
        session = ChatSession.objects.filter(id=session_id, user=user).first()
        if session:
            return session
    return ChatSession.objects.create(user=user, title=first_message[:36] or "新的运营咨询")


def seed_default_categories() -> None:
    default_categories = [
        ("美妆个护", "美妆、护肤、香氛、个护清洁"),
        ("服饰穿搭", "服装、鞋靴、配饰、穿搭内容"),
        ("箱包配饰", "女包、通勤包、饰品、帽子"),
        ("家居收纳", "家居用品、收纳整理、租房好物"),
        ("数码配件", "手机配件、桌面设备、智能硬件"),
        ("母婴亲子", "母婴用品、玩具、亲子内容"),
        ("宠物用品", "宠物食品、清洁、玩具和出行用品"),
        ("食品饮料", "零食、饮品、轻食、地方特产"),
        ("运动户外", "运动装备、户外用品、健身内容"),
        ("跨境电商", "TikTok、Amazon、独立站相关选品"),
    ]
    if TrendingCategory.objects.exists():
        return
    for index, (name, description) in enumerate(default_categories, start=1):
        TrendingCategory.objects.create(name=name, description=description, sort_order=index)


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "account_id": user.account_id,
        "display_name": user.display_name,
        "role": user.role,
        "preferences": user.preferences,
        "created_at": iso(user.created_at),
    }


def serialize_session(session: ChatSession) -> dict:
    preview_source = session.session_summary or session.user_transcript
    preview = preview_source.replace("\n", " ")[:96]
    return {
        "id": session.id,
        "title": session.title,
        "message_count": session.message_count,
        "last_message_at": iso(session.last_message_at) if session.last_message_at else None,
        "preview": preview,
        "created_at": iso(session.created_at),
        "updated_at": iso(session.updated_at),
    }


def serialize_session_detail(session: ChatSession) -> dict:
    return {
        **serialize_session(session),
        "user_transcript": session.user_transcript,
        "assistant_transcript": session.assistant_transcript,
        "session_summary": session.session_summary,
        "trace_summary": session.trace_summary,
        "recent_interactions": session.recent_interactions,
    }


def serialize_trending_item(item: TrendingItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "source": item.source,
        "summary": item.summary,
        "heat_score": item.heat_score,
        "tags": item.tags,
        "created_by": item.created_by_id,
        "visibility": item.visibility,
        "is_ai_generated": item.is_ai_generated,
        "created_at": iso(item.created_at),
        "updated_at": iso(item.updated_at),
    }


def serialize_user_insight(user: User, profile: UserProfile | None) -> dict:
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "account_id": user.account_id,
        "preferred_categories": profile.preferred_categories if profile else user.preferences.get("preferred_categories", []),
        "preferred_platforms": profile.preferred_platforms if profile else user.preferences.get("preferred_platforms", []),
        "summary": profile.summary if profile else "",
        "interest_weights": profile.interest_weights if profile else {},
        "negative_preferences": profile.negative_preferences if profile else [],
        "recall_score": profile.recall_score if profile else 0,
        "interaction_frequency": profile.interaction_frequency if profile else 0,
        "last_active_at": iso(profile.last_active_at) if profile and profile.last_active_at else None,
        "updated_at": iso(profile.updated_at) if profile else None,
    }


def serialize_document(document: UploadedDocument) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "category": document.category,
        "visibility": document.visibility,
        "vectorized": document.vectorized,
        "created_at": iso(document.created_at),
    }


def serialize_memory(memory: UserMemory) -> dict:
    return {
        "id": memory.id,
        "user_id": memory.user_id,
        "short_messages": memory.short_messages,
        "short_term_summary": memory.short_term_summary,
        "long_term_summary": memory.long_term_summary,
        "preferences": memory.preferences,
        "negative_preferences": memory.negative_preferences,
        "business_needs": memory.business_needs,
        "behavior_notes": memory.behavior_notes,
        "recall_signals": memory.recall_signals,
        "tags": memory.tags,
        "confidence": memory.confidence,
        "last_used_at": iso(memory.last_used_at) if memory.last_used_at else None,
        "created_at": iso(memory.created_at),
        "updated_at": iso(memory.updated_at),
    }


def serialize_profile_for_agent(user: User, profile: UserProfile | None) -> dict:
    return {
        "user_id": user.id,
        "summary": profile.summary if profile else "",
        "interest_weights": profile.interest_weights if profile else {},
        "negative_preferences": profile.negative_preferences if profile else [],
        "preferred_platforms": profile.preferred_platforms if profile else user.preferences.get("preferred_platforms", []),
        "preferred_categories": profile.preferred_categories if profile else user.preferences.get("preferred_categories", []),
        "recall_score": profile.recall_score if profile else 0,
        "interaction_frequency": profile.interaction_frequency if profile else 0,
        "last_active_at": iso(profile.last_active_at) if profile and profile.last_active_at else None,
        "updated_at": iso(profile.updated_at) if profile else None,
    }


def serialize_trend_for_agent(item: TrendingItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "summary": item.summary,
        "heat_score": item.heat_score,
        "tags": item.tags,
    }


def serialize_recall_record(record: RecallRecord) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "recall_score": record.recall_score,
        "matched_trends": record.matched_trends,
        "generated_message": record.generated_message,
        "created_at": iso(record.created_at),
        "created_by": record.created_by_id,
    }


def ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
    return []


def merge_unique(existing: object, additions: list[str], limit: int = 50) -> list[str]:
    seen = set()
    result = []
    for value in [*ensure_list(existing), *ensure_list(additions)]:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result[-limit:]


def merge_weights(existing: object, additions: dict[str, float]) -> dict[str, float]:
    weights = dict(existing or {}) if isinstance(existing, dict) else {}
    for key, value in additions.items():
        label = str(key).strip()
        if not label:
            continue
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = 0.5
        weights[label] = max(float(weights.get(label, 0)), max(0.0, min(score, 1.0)))
    return weights


def merge_memory_preferences(existing: object, additions: list[str]) -> dict:
    preferences = dict(existing or {}) if isinstance(existing, dict) else {}
    current = ensure_list(preferences.get("profile_preferences"))
    merged = merge_unique(current, additions)
    if merged:
        preferences["profile_preferences"] = merged
    return preferences


def iso(value) -> str:
    return value.isoformat() if value else ""


def error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def method_not_allowed() -> JsonResponse:
    return error("Method not allowed", 405)
