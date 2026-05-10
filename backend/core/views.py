from __future__ import annotations

import json
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from agents import AgentOrchestrator
from agents.user_profile_agent import UserProfileAgent
from agents.user_recall_agent import RecallAgent

from .models import (
    ChatMessage,
    ChatSession,
    RecallRecord,
    TrendingCategory,
    TrendingItem,
    UploadedDocument,
    User,
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
        password_hash=make_password(password),
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
    return JsonResponse(auth_response(user))


@csrf_exempt
def login(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return method_not_allowed()
    payload = read_json(request)
    identifier = str(payload.get("identifier", "")).strip()
    password = str(payload.get("password", ""))
    user = User.objects.filter(Q(account_id=identifier) | Q(display_name=identifier)).first()
    if not user or not check_password(password, user.password_hash):
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
    content = str(payload.get("content", "")).strip()
    if not content:
        return error("Message cannot be empty", 400)
    session = get_or_create_session(user, payload.get("session_id"), content)
    ChatMessage.objects.create(session=session, user=user, role="user", content=content)
    trend_titles = list(
        TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at").values_list("title", flat=True)[:5]
    )
    messages = AgentOrchestrator().run(content, trend_titles)
    for message in messages:
        ChatMessage.objects.create(
            session=session,
            user=user,
            role="assistant",
            content=message["content"],
            message_type=message["type"],
            agent_name=message["agent"],
            agent_function=message.get("function"),
        )
    update_profile_from_text(user, content)
    session.save(update_fields=["updated_at"])
    return JsonResponse({"session_id": session.id, "messages": messages})


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


def chat_history(request: HttpRequest) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    session = ChatSession.objects.filter(id=request.GET.get("session_id"), user=user).first()
    if not session:
        return error("Session not found", 404)
    messages = ChatMessage.objects.filter(session=session).order_by("created_at")
    return JsonResponse([serialize_chat_message(message) for message in messages], safe=False)


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
    for user in User.objects.exclude(role="admin"):
        profile = getattr(user, "profile", None)
        frequency = profile.interaction_frequency if profile else 0
        weights = profile.interest_weights if profile else {}
        score = min(0.25 + frequency * 0.06 + len(weights) * 0.04, 0.98)
        result.append(
            {
                "user_id": user.id,
                "display_name": user.display_name,
                "account_id": user.account_id,
                "last_active_at": iso(profile.last_active_at) if profile and profile.last_active_at else None,
                "preferred_categories": profile.preferred_categories if profile else user.preferences.get("preferred_categories", []),
                "recall_score": round(score, 2),
                "reason": "基于历史关注类目、交互频率和近期爆品匹配度生成。",
            }
        )
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
    trends = list(TrendingItem.objects.filter(visibility="public").order_by("-heat_score", "-created_at").values_list("title", flat=True)[:5])
    frequency = profile.interaction_frequency if profile else 0
    weights = profile.interest_weights if profile else {}
    score = min(0.35 + frequency * 0.06 + len(weights) * 0.04, 0.98)
    categories = profile.preferred_categories if profile else user.preferences.get("preferred_categories", [])
    generated = RecallAgent().generate(user.display_name, categories, trends, score)
    RecallRecord.objects.create(
        user=user,
        recall_score=generated["recall_score"],
        matched_trends=generated["matched_trends"],
        generated_message=generated["message"],
        created_by=admin,
    )
    return JsonResponse({"user_id": user.id, **generated})


def user_memory(request: HttpRequest, user_id: str) -> JsonResponse:
    user = current_user(request)
    if not user:
        return error("Invalid or expired token", 401)
    if user.role != "admin" and user.id != user_id:
        return error("Cannot access this memory", 403)
    profile = UserProfile.objects.filter(user_id=user_id).first()
    return JsonResponse({"user_id": user_id, "summary": profile.summary if profile else "", "interest_weights": profile.interest_weights if profile else {}})


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
    profile, _ = UserProfile.objects.get_or_create(user=target, defaults={"summary": "暂无足够对话形成长期记忆。"})
    return JsonResponse({"status": "ok", "summary": profile.summary})


def read_json(request: HttpRequest) -> dict:
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


def auth_response(user: User) -> dict:
    return {"access_token": signer.sign(user.id), "token_type": "bearer", "user": serialize_user(user)}


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


def update_profile_from_text(user: User, content: str) -> None:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    weights = dict(profile.interest_weights or {})
    tags = UserProfileAgent().extract_tags(content)
    for tag in tags:
        weights[tag] = min(float(weights.get(tag, 0.2)) + 0.08, 1.0)
    profile.interest_weights = weights
    profile.interaction_frequency = (profile.interaction_frequency or 0) + 1
    profile.last_active_at = timezone.now()
    if tags:
        profile.summary = f"用户最近关注：{', '.join(sorted(set(tags)))}。"
    profile.save()


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
    return {"id": session.id, "title": session.title, "created_at": iso(session.created_at), "updated_at": iso(session.updated_at)}


def serialize_chat_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "session_id": message.session_id,
        "role": message.role,
        "content": message.content,
        "message_type": message.message_type,
        "agent_name": message.agent_name,
        "agent_function": message.agent_function,
        "created_at": iso(message.created_at),
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


def ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
    return []


def iso(value) -> str:
    return value.isoformat() if value else ""


def error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"detail": message}, status=status)


def method_not_allowed() -> JsonResponse:
    return error("Method not allowed", 405)
