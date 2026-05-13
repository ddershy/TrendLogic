<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { api, setToken } from "./api/client";
import type {
  AgentMessage,
  ChatSessionSummary,
  RAGSearchResult,
  RecallCandidate,
  TrendingItem,
  UploadedDocument,
  User,
  UserInsight,
  UserMemoryProfile
} from "./types";

type ViewName = "chat" | "trending" | "user-insights" | "memory" | "recall" | "rag";
type AuthMode = "login" | "register";

interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  trace?: AgentMessage;
}

interface MemoryDraft {
  short_term_summary: string;
  long_term_summary: string;
  preferences_json: string;
  negative_preferences_text: string;
  business_needs_text: string;
  behavior_notes_text: string;
  recall_signals_json: string;
  tags_text: string;
  confidence: number;
}

const user = ref<User | null>(null);
const authOpen = ref(true);
const authMode = ref<AuthMode>("login");
const authError = ref("");
const identifier = ref("");
const displayName = ref("");
const password = ref("");
const categoriesText = ref("美妆个护, 家居收纳");
const platformsText = ref("小红书, 抖音");
const businessFocus = ref("");
const adminCode = ref("");
const currentView = ref<ViewName>("chat");

const chatEntries = ref<ChatEntry[]>([]);
const sessionId = ref<string | null>(null);
const chatText = ref("");
const chatLoading = ref(false);
const showPendingAnalysis = ref(false);
const chatError = ref("");
const chatSessions = ref<ChatSessionSummary[]>([]);
const historyLoading = ref(false);
const deletingSessionId = ref("");
const openTraceGroups = ref<Record<string, boolean>>({});
const messageBottom = ref<HTMLDivElement | null>(null);

const trendingItems = ref<TrendingItem[]>([]);
const trendingCategories = ref<string[]>([]);
const activeCategory = ref("全部");
const trendTitle = ref("");
const trendCategory = ref("");
const trendSummary = ref("");
const trendTags = ref("");
const trendRefreshing = ref(false);
const deletingTrendId = ref("");
const trendError = ref("");

const insights = ref<UserInsight[]>([]);
const selectedMemoryUserId = ref("");
const activeMemory = ref<UserMemoryProfile | null>(null);
const memoryDraft = ref<MemoryDraft>(emptyMemoryDraft());
const memoryLoading = ref(false);
const memorySaving = ref(false);
const memoryError = ref("");
const memoryStatus = ref("");
const recallItems = ref<RecallCandidate[]>([]);
const recallMessage = ref("");
const recallGeneratingUserId = ref("");
const adminError = ref("");
const ragDocuments = ref<UploadedDocument[]>([]);
const ragFile = ref<File | null>(null);
const ragCategory = ref("选品资料");
const ragQuery = ref("");
const ragSearchCategory = ref("");
const ragResults = ref<RAGSearchResult[]>([]);
const ragLoading = ref(false);
const ragIndexingId = ref("");
const ragDeletingId = ref("");
const ragStatus = ref("");
const ragError = ref("");

const navItems = computed(() => [
  { key: "chat" as const, label: "智能运营台", adminOnly: false },
  { key: "trending" as const, label: "最新爆品", adminOnly: false },
  { key: "user-insights" as const, label: "用户洞察", adminOnly: true },
  { key: "memory" as const, label: "记忆档案", adminOnly: true },
  { key: "recall" as const, label: "一键召回", adminOnly: true },
  { key: "rag" as const, label: "知识库", adminOnly: true }
]);

const visibleNavItems = computed(() => navItems.value.filter((item) => !item.adminOnly || user.value?.role === "admin"));
const selectedMemoryUser = computed(() => insights.value.find((item) => item.user_id === selectedMemoryUserId.value) ?? null);
const visibleChatEntries = computed(() =>
  chatLoading.value && showPendingAnalysis.value
    ? [
        ...chatEntries.value,
        {
          id: "pending-analysis",
          role: "assistant" as const,
          content: "我正在整理你的问题，先判断它属于哪个运营场景，再决定是否需要补充关键信息。"
        }
      ]
    : chatEntries.value
);
const groupedChatItems = computed(() => groupChatEntries(visibleChatEntries.value));
const categoryCounts = computed(() => {
  const counts: Record<string, number> = { 全部: trendingItems.value.length };
  for (const item of trendingItems.value) {
    counts[item.category] = (counts[item.category] ?? 0) + 1;
  }
  return counts;
});
const visibleCategories = computed(() => {
  const names = new Set(trendingCategories.value);
  for (const item of trendingItems.value) {
    names.add(item.category);
  }
  return ["全部", ...Array.from(names)];
});
const filteredTrendingItems = computed(() =>
  activeCategory.value === "全部" ? trendingItems.value : trendingItems.value.filter((item) => item.category === activeCategory.value)
);
const ragCategories = computed(() => {
  const names = new Set(["选品资料", "平台规则", "运营案例", "用户研究"]);
  for (const document of ragDocuments.value) {
    names.add(document.category);
  }
  return Array.from(names);
});

onMounted(async () => {
  try {
    user.value = await api.me();
    authOpen.value = false;
    await Promise.all([loadTrending(), loadChatSessions()]);
  } catch {
    setToken(null);
  }
});

watch([visibleChatEntries, openTraceGroups], async () => {
  await scrollToMessageBottom();
});

watch(chatEntries, async () => {
  await scrollToMessageBottom();
}, {
  deep: true
});

async function submitAuth() {
  authError.value = "";
  try {
    const response =
      authMode.value === "login"
        ? await api.login(identifier.value, password.value)
        : await api.register({
            display_name: displayName.value,
            password: password.value,
            preferred_categories: splitTags(categoriesText.value),
            preferred_platforms: splitTags(platformsText.value),
            business_focus: businessFocus.value,
            admin_invite_code: adminCode.value || undefined
          });
    setToken(response.access_token);
    user.value = response.user;
    clearAuthForm();
    authOpen.value = false;
    await Promise.all([loadTrending(), loadChatSessions()]);
  } catch (error) {
    authError.value = error instanceof Error ? error.message : "操作失败";
  }
}

function openAuth(mode: AuthMode) {
  authMode.value = mode;
  authOpen.value = true;
}

function closeAuth() {
  clearAuthForm();
  authOpen.value = false;
}

function clearAuthForm() {
  identifier.value = "";
  displayName.value = "";
  password.value = "";
  categoriesText.value = "";
  platformsText.value = "";
  businessFocus.value = "";
  adminCode.value = "";
  authError.value = "";
}

function logout() {
  setToken(null);
  user.value = null;
  authOpen.value = true;
  chatSessions.value = [];
  sessionId.value = null;
  chatEntries.value = [];
}

async function loadChatSessions() {
  if (!user.value) return;
  try {
    chatSessions.value = await api.listChatSessions();
  } catch (error) {
    chatError.value = error instanceof Error ? error.message : "历史会话加载失败";
  }
}

async function startNewChat() {
  sessionId.value = null;
  chatEntries.value = [];
  openTraceGroups.value = {};
  chatError.value = "";
}

async function loadChatSession(id: string) {
  if (!user.value) return;
  historyLoading.value = true;
  chatError.value = "";
  try {
    const history = await api.getChatHistory(id);
    sessionId.value = history.id;
    chatEntries.value = history.session_summary
      ? [{ id: crypto.randomUUID(), role: "assistant", content: `会话摘要\n${history.session_summary}` }]
      : history.user_transcript
      ? [{ id: crypto.randomUUID(), role: "user", content: history.user_transcript }]
      : [];
    openTraceGroups.value = {};
  } catch (error) {
    chatError.value = error instanceof Error ? error.message : "历史会话加载失败";
  } finally {
    historyLoading.value = false;
  }
}

async function deleteChatSession(item: ChatSessionSummary) {
  const confirmed = window.confirm(`确定删除“${item.title}”吗？`);
  if (!confirmed) return;
  deletingSessionId.value = item.id;
  chatError.value = "";
  try {
    await api.deleteChatSession(item.id);
    chatSessions.value = chatSessions.value.filter((session) => session.id !== item.id);
    if (sessionId.value === item.id) {
      sessionId.value = null;
      chatEntries.value = [];
      openTraceGroups.value = {};
    }
  } catch (error) {
    chatError.value = error instanceof Error ? error.message : "删除历史会话失败";
  } finally {
    deletingSessionId.value = "";
  }
}

async function sendMessage() {
  if (!chatText.value.trim() || !user.value) return;
  const text = chatText.value.trim();
  chatText.value = "";
  chatError.value = "";
  chatEntries.value.push({ id: crypto.randomUUID(), role: "user", content: text });
  chatLoading.value = true;
  showPendingAnalysis.value = true;
  let finalEntryId = "";
  try {
    await api.sendMessageStream(text, sessionId.value, (event) => {
      if (event.event === "session" || event.event === "done") {
        sessionId.value = event.session_id;
        return;
      }
      showPendingAnalysis.value = false;
      if (event.event === "process") {
        chatEntries.value.push({ id: crypto.randomUUID(), role: "assistant", content: event.message.content, trace: event.message });
        void scrollToMessageBottom();
        return;
      }
      if (event.event === "final_start") {
        finalEntryId = crypto.randomUUID();
        chatEntries.value.push({ id: finalEntryId, role: "assistant", content: "" });
        void scrollToMessageBottom();
        return;
      }
      if (event.event === "final_delta") {
        const target = chatEntries.value.find((entry) => entry.id === finalEntryId);
        if (target) {
          target.content += event.content;
          void scrollToMessageBottom();
        }
      }
    });
    await loadChatSessions();
  } catch (error) {
    chatError.value = error instanceof Error ? error.message : "发送失败";
  } finally {
    chatLoading.value = false;
    showPendingAnalysis.value = false;
  }
}

async function loadTrending() {
  if (!user.value) return;
  trendRefreshing.value = true;
  trendError.value = "";
  try {
    const [items, categories] = await Promise.all([api.listTrending(), api.listTrendingCategories()]);
    trendingItems.value = items;
    trendingCategories.value = categories;
    trendCategory.value = trendCategory.value || categories[0] || "";
    if (activeCategory.value !== "全部" && !categories.includes(activeCategory.value)) {
      activeCategory.value = "全部";
    }
  } catch (error) {
    trendError.value = error instanceof Error ? error.message : "加载失败";
  } finally {
    trendRefreshing.value = false;
  }
}

async function createTrendingItem() {
  if (!user.value) return;
  try {
    const item = await api.createTrending({
      title: trendTitle.value,
      category: trendCategory.value,
      summary: trendSummary.value,
      source: "user_upload",
      heat_score: 0.7,
      tags: splitTags(trendTags.value),
      visibility: "public",
      is_ai_generated: false
    });
    trendingItems.value = [item, ...trendingItems.value];
    activeCategory.value = item.category;
    trendTitle.value = "";
    trendCategory.value = trendingCategories.value[0] || item.category;
    trendSummary.value = "";
    trendTags.value = "";
  } catch (error) {
    trendError.value = error instanceof Error ? error.message : "发布失败";
  }
}

async function deleteTrendingItem(item: TrendingItem) {
  if (user.value?.role !== "admin") return;
  const confirmed = window.confirm(`确定删除“${item.title}”吗？`);
  if (!confirmed) return;
  deletingTrendId.value = item.id;
  trendError.value = "";
  try {
    await api.deleteTrending(item.id);
    trendingItems.value = trendingItems.value.filter((current) => current.id !== item.id);
    if (activeCategory.value !== "全部" && !filteredTrendingItems.value.length) {
      activeCategory.value = "全部";
    }
  } catch (error) {
    trendError.value = error instanceof Error ? error.message : "删除失败";
  } finally {
    deletingTrendId.value = "";
  }
}

async function loadInsights() {
  if (user.value?.role !== "admin") return;
  adminError.value = "";
  try {
    insights.value = await api.userInsights();
  } catch (error) {
    adminError.value = error instanceof Error ? error.message : "加载失败";
  }
}

async function loadMemoryModule() {
  if (user.value?.role !== "admin") return;
  memoryError.value = "";
  try {
    if (!insights.value.length) {
      await loadInsights();
    }
    if (!selectedMemoryUserId.value && insights.value.length) {
      selectedMemoryUserId.value = insights.value[0].user_id;
    }
    if (selectedMemoryUserId.value) {
      await loadSelectedMemory();
    }
  } catch (error) {
    memoryError.value = error instanceof Error ? error.message : "记忆档案加载失败";
  }
}

async function selectMemoryUser(userId: string) {
  selectedMemoryUserId.value = userId;
  await loadSelectedMemory();
}

async function loadSelectedMemory() {
  if (!selectedMemoryUserId.value) return;
  memoryLoading.value = true;
  memoryError.value = "";
  memoryStatus.value = "";
  try {
    const response = await api.getUserMemory(selectedMemoryUserId.value);
    activeMemory.value = response.memory;
    fillMemoryDraft(response.memory);
  } catch (error) {
    memoryError.value = error instanceof Error ? error.message : "记忆档案加载失败";
  } finally {
    memoryLoading.value = false;
  }
}

async function saveMemory() {
  if (!selectedMemoryUserId.value) return;
  memorySaving.value = true;
  memoryError.value = "";
  memoryStatus.value = "";
  try {
    const response = await api.updateUserMemory(selectedMemoryUserId.value, {
      short_term_summary: memoryDraft.value.short_term_summary,
      long_term_summary: memoryDraft.value.long_term_summary,
      preferences: parseJson(memoryDraft.value.preferences_json, {}),
      negative_preferences: splitLines(memoryDraft.value.negative_preferences_text),
      business_needs: splitLines(memoryDraft.value.business_needs_text),
      behavior_notes: splitLines(memoryDraft.value.behavior_notes_text),
      recall_signals: parseJson(memoryDraft.value.recall_signals_json, []),
      tags: splitTags(memoryDraft.value.tags_text),
      confidence: memoryDraft.value.confidence
    });
    activeMemory.value = response.memory;
    fillMemoryDraft(response.memory);
    memoryStatus.value = "记忆档案已保存";
  } catch (error) {
    memoryError.value = error instanceof Error ? error.message : "保存失败，请检查 JSON 格式";
  } finally {
    memorySaving.value = false;
  }
}

async function summarizeSelectedMemory() {
  if (!selectedMemoryUserId.value) return;
  memorySaving.value = true;
  memoryError.value = "";
  memoryStatus.value = "";
  try {
    const response = await api.summarizeUserMemory(selectedMemoryUserId.value);
    activeMemory.value = response.memory;
    fillMemoryDraft(response.memory);
    memoryStatus.value = "已根据最近会话更新长期记忆";
  } catch (error) {
    memoryError.value = error instanceof Error ? error.message : "生成长期记忆失败";
  } finally {
    memorySaving.value = false;
  }
}

async function loadRecall() {
  if (user.value?.role !== "admin") return;
  adminError.value = "";
  try {
    recallItems.value = await api.recallCandidates();
  } catch (error) {
    adminError.value = error instanceof Error ? error.message : "加载失败";
  }
}

async function loadRagDocuments() {
  if (user.value?.role !== "admin") return;
  ragLoading.value = true;
  ragError.value = "";
  try {
    ragDocuments.value = await api.listRagDocuments();
  } catch (error) {
    ragError.value = error instanceof Error ? error.message : "知识库加载失败";
  } finally {
    ragLoading.value = false;
  }
}

function selectRagFile(event: Event) {
  const target = event.target as HTMLInputElement;
  ragFile.value = target.files?.[0] ?? null;
}

async function uploadRagDocument() {
  if (!ragFile.value) {
    ragError.value = "请选择要上传的文档";
    return;
  }
  ragLoading.value = true;
  ragError.value = "";
  ragStatus.value = "";
  try {
    const document = await api.uploadRagDocument(ragFile.value, ragCategory.value);
    ragDocuments.value = [document, ...ragDocuments.value.filter((item) => item.id !== document.id)];
    ragStatus.value = `已上传并索引 ${document.chunk_count} 个分块`;
    ragFile.value = null;
  } catch (error) {
    ragError.value = error instanceof Error ? error.message : "上传或索引失败";
  } finally {
    ragLoading.value = false;
  }
}

async function reindexRagDocument(document: UploadedDocument) {
  ragIndexingId.value = document.id;
  ragError.value = "";
  ragStatus.value = "";
  try {
    const updated = await api.reindexRagDocument(document.id);
    ragDocuments.value = ragDocuments.value.map((item) => (item.id === updated.id ? updated : item));
    ragStatus.value = `已重建索引：${updated.chunk_count} 个分块`;
  } catch (error) {
    ragError.value = error instanceof Error ? error.message : "重建索引失败";
  } finally {
    ragIndexingId.value = "";
  }
}

async function deleteRagDocument(document: UploadedDocument) {
  const confirmed = window.confirm(`确定删除“${document.filename}”吗？`);
  if (!confirmed) return;
  ragDeletingId.value = document.id;
  ragError.value = "";
  ragStatus.value = "";
  try {
    await api.deleteRagDocument(document.id);
    ragDocuments.value = ragDocuments.value.filter((item) => item.id !== document.id);
    ragResults.value = ragResults.value.filter((item) => item.metadata.document_id !== document.id);
    ragStatus.value = "文档已删除";
  } catch (error) {
    ragError.value = error instanceof Error ? error.message : "删除文档失败";
  } finally {
    ragDeletingId.value = "";
  }
}

async function searchRagDocuments() {
  if (!ragQuery.value.trim()) {
    ragError.value = "请输入检索问题";
    return;
  }
  ragLoading.value = true;
  ragError.value = "";
  ragStatus.value = "";
  try {
    const response = await api.searchRag(ragQuery.value.trim(), 5, ragSearchCategory.value || undefined);
    ragResults.value = response.results;
    ragStatus.value = `检索完成，命中 ${response.results.length} 个分块`;
  } catch (error) {
    ragError.value = error instanceof Error ? error.message : "检索失败";
  } finally {
    ragLoading.value = false;
  }
}

async function switchView(view: ViewName) {
  currentView.value = view;
  if (view === "trending") await loadTrending();
  if (view === "chat") await loadChatSessions();
  if (view === "user-insights") await loadInsights();
  if (view === "memory") await loadMemoryModule();
  if (view === "recall") await loadRecall();
  if (view === "rag") await loadRagDocuments();
}

async function generateRecall(userId: string) {
  recallGeneratingUserId.value = userId;
  adminError.value = "";
  try {
    const result = await api.generateRecall(userId);
    const meta = [
      result.reason ? `生成理由：${result.reason}` : "",
      result.recommended_channel ? `建议渠道：${result.recommended_channel}` : "",
      result.timing ? `建议时机：${result.timing}` : ""
    ].filter(Boolean);
    recallMessage.value = meta.length ? `${result.message}\n\n${meta.join("\n")}` : result.message;
    await loadRecall();
  } catch (error) {
    adminError.value = error instanceof Error ? error.message : "生成失败";
  } finally {
    recallGeneratingUserId.value = "";
  }
}

function copyRecallMessage() {
  navigator.clipboard.writeText(recallMessage.value);
}

async function scrollToMessageBottom() {
  await nextTick();
  messageBottom.value?.scrollIntoView({ behavior: "smooth", block: "end" });
}

function splitTags(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function splitLines(value: string) {
  return value
    .split(/\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function toLines(value: unknown) {
  return Array.isArray(value) ? value.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join("\n") : "";
}

function parseJson(value: string, fallback: unknown) {
  const text = value.trim();
  if (!text) return fallback;
  return JSON.parse(text);
}

function renderMarkdown(value: string) {
  const escaped = escapeHtml(value);
  const blocks = escaped.split(/\n{2,}/).map((block) => {
    const trimmed = block.trim();
    if (!trimmed) return "";
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length + 2;
      return `<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`;
    }
    const lines = trimmed.split("\n");
    if (lines.every((line) => /^[-*]\s+/.test(line.trim()))) {
      return `<ul>${lines.map((line) => `<li>${renderInlineMarkdown(line.trim().replace(/^[-*]\s+/, ""))}</li>`).join("")}</ul>`;
    }
    if (lines.every((line) => /^\d+\.\s+/.test(line.trim()))) {
      return `<ol>${lines.map((line) => `<li>${renderInlineMarkdown(line.trim().replace(/^\d+\.\s+/, ""))}</li>`).join("")}</ol>`;
    }
    return `<p>${renderInlineMarkdown(trimmed).replace(/\n/g, "<br>")}</p>`;
  });
  return blocks.join("");
}

function renderInlineMarkdown(value: string) {
  return value
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function emptyMemoryDraft(): MemoryDraft {
  return {
    short_term_summary: "",
    long_term_summary: "",
    preferences_json: "{}",
    negative_preferences_text: "",
    business_needs_text: "",
    behavior_notes_text: "",
    recall_signals_json: "[]",
    tags_text: "",
    confidence: 0.7
  };
}

function fillMemoryDraft(memory: UserMemoryProfile) {
  memoryDraft.value = {
    short_term_summary: memory.short_term_summary,
    long_term_summary: memory.long_term_summary,
    preferences_json: JSON.stringify(memory.preferences ?? {}, null, 2),
    negative_preferences_text: toLines(memory.negative_preferences),
    business_needs_text: toLines(memory.business_needs),
    behavior_notes_text: toLines(memory.behavior_notes),
    recall_signals_json: JSON.stringify(memory.recall_signals ?? [], null, 2),
    tags_text: (memory.tags ?? []).join(", "),
    confidence: memory.confidence
  };
}

function groupChatEntries(entries: ChatEntry[]) {
  const items: Array<{ kind: "message"; entry: ChatEntry } | { kind: "traceGroup"; id: string; traces: AgentMessage[] }> = [];
  let traces: AgentMessage[] = [];
  let groupId = "";
  const flush = () => {
    if (!traces.length) return;
    items.push({ kind: "traceGroup", id: groupId, traces });
    traces = [];
    groupId = "";
  };
  for (const entry of entries) {
    if (entry.trace) {
      if (!traces.length) groupId = entry.id;
      traces.push(entry.trace);
    } else {
      flush();
      items.push({ kind: "message", entry });
    }
  }
  flush();
  return items;
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brandIcon">TL</div>
        <div>
          <strong>TrendLogic</strong>
          <span>AI 电商运营助手</span>
        </div>
      </div>
      <nav>
        <button
          v-for="item in visibleNavItems"
          :key="item.key"
          :class="currentView === item.key ? 'navItem active' : 'navItem'"
          @click="switchView(item.key)"
        >
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <strong>{{ user ? user.display_name : "未登录访客" }}</strong>
          <span>{{ user ? `${user.account_id} · ${user.role}` : "登录后可使用核心功能" }}</span>
        </div>
        <button v-if="user" class="ghostButton" @click="logout">退出</button>
        <div v-else class="topbarActions">
          <button class="ghostButton" @click="openAuth('login')">登录</button>
          <button class="primaryButton" @click="openAuth('register')">注册</button>
        </div>
      </header>

      <section v-if="currentView === 'chat'" class="page chatPage">
        <div class="pageTitle">
          <div>
            <h1>智能运营台</h1>
            <p>输入平台、类目、预算或运营目标，系统会路由到合适的 Agent。</p>
          </div>
        </div>
        <div class="chatWorkspace">
          <aside class="chatHistoryPanel">
            <div class="historyHeader">
              <strong>历史会话</strong>
              <button class="ghostButton" type="button" @click="startNewChat">新对话</button>
            </div>
            <div v-if="chatSessions.length" class="historyList">
              <div
                v-for="item in chatSessions"
                :key="item.id"
                :class="sessionId === item.id ? 'historyItemShell active' : 'historyItemShell'"
              >
                <button
                  type="button"
                  class="historyItem"
                  :disabled="historyLoading || deletingSessionId === item.id"
                  @click="loadChatSession(item.id)"
                >
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.message_count }} 条用户输入</span>
                  <small>{{ item.preview || "暂无内容" }}</small>
                </button>
                <button
                  class="historyDeleteButton"
                  type="button"
                  :disabled="deletingSessionId === item.id"
                  aria-label="删除历史会话"
                  @click="deleteChatSession(item)"
                >
                  {{ deletingSessionId === item.id ? "..." : "删除" }}
                </button>
              </div>
            </div>
            <div v-else class="historyEmpty">登录后产生的每次完整对话会保存在这里。</div>
          </aside>
          <div class="chatSurface">
            <div v-if="visibleChatEntries.length" class="messageList">
              <template v-for="item in groupedChatItems" :key="item.kind === 'traceGroup' ? item.id : item.entry.id">
                <div v-if="item.kind === 'traceGroup'" class="traceGroup">
                  <button
                    type="button"
                    class="traceToggle"
                    @click="openTraceGroups[item.id] = !openTraceGroups[item.id]"
                  >
                    <span>{{ openTraceGroups[item.id] ? "⌄" : "›" }}</span>
                    <span>Agent 执行过程 · {{ item.traces.length }} 条</span>
                  </button>
                  <div v-if="openTraceGroups[item.id]" class="tracePanel">
                    <div v-for="(trace, index) in item.traces" :key="`${item.id}-${index}`" class="traceLine">
                      <strong>[{{ trace.agent }}/{{ trace.function ?? "执行日志" }}]</strong>
                      <p>{{ trace.content }}</p>
                    </div>
                  </div>
                </div>
                <div v-else :class="`bubbleRow ${item.entry.role}`">
                  <div class="bubble markdownBody" v-html="renderMarkdown(item.entry.content)" />
                </div>
              </template>
              <div ref="messageBottom" />
            </div>
            <div v-else class="emptyState">可以试试：“我想在小红书做美妆选品，预算 5000 元，适合卖什么？”</div>
            <form class="composer" @submit.prevent="sendMessage">
              <input v-model="chatText" :disabled="!user || chatLoading" placeholder="描述你的选品、流量或带货问题" />
              <button class="primaryIconButton" :disabled="!user || chatLoading" aria-label="发送">发送</button>
            </form>
            <p v-if="chatError" class="inlineError">{{ chatError }}</p>
          </div>
        </div>
      </section>

      <section v-if="currentView === 'trending'" class="page">
        <div class="pageTitle">
          <div>
            <h1>最新爆品</h1>
            <p>查看公开热点，普通用户可上传公开条目，内部 RAG 文档仅 admin 上传。</p>
          </div>
          <button class="ghostButton" :disabled="trendRefreshing" @click="loadTrending">
            <span :class="trendRefreshing ? 'spinIcon refreshMark' : 'refreshMark'">↻</span>
            {{ trendRefreshing ? "刷新中" : "刷新" }}
          </button>
        </div>
        <div class="categoryBar" aria-label="爆品分类">
          <button
            v-for="item in visibleCategories"
            :key="item"
            type="button"
            :class="activeCategory === item ? 'categoryPill active' : 'categoryPill'"
            @click="activeCategory = item"
          >
            <span>{{ item }}</span>
            <strong>{{ categoryCounts[item] ?? 0 }}</strong>
          </button>
        </div>
        <div class="contentGrid">
          <form class="sideForm" @submit.prevent="createTrendingItem">
            <h2>上传热点</h2>
            <label>标题<input v-model="trendTitle" required /></label>
            <label>
              类目
              <select v-model="trendCategory" required>
                <option v-for="item in trendingCategories" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label>摘要<textarea v-model="trendSummary" required /></label>
            <label>标签<input v-model="trendTags" placeholder="小红书, 女包" /></label>
            <button class="primaryButton" :disabled="!user">发布</button>
          </form>
          <div class="itemList">
            <p v-if="trendError" class="inlineError">{{ trendError }}</p>
            <div class="listHeader">
              <strong>{{ activeCategory === "全部" ? "全部爆品" : activeCategory }}</strong>
              <span>{{ filteredTrendingItems.length }} 条内容</span>
            </div>
            <div v-if="filteredTrendingItems.length === 0" class="emptyState">这个分类下还没有条目，可以在左侧上传一条新的热点内容。</div>
            <article v-for="item in filteredTrendingItems" :key="item.id" class="trendCard">
              <div class="trendHeader">
                <strong>{{ item.title }}</strong>
                <button
                  v-if="user?.role === 'admin'"
                  class="dangerButton"
                  type="button"
                  :disabled="deletingTrendId === item.id"
                  @click="deleteTrendingItem(item)"
                >
                  {{ deletingTrendId === item.id ? "删除中" : "删除" }}
                </button>
              </div>
              <p>{{ item.summary }}</p>
              <div class="tagRow">
                <span>{{ item.category }}</span>
                <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
              </div>
            </article>
          </div>
        </div>
      </section>

      <section v-if="currentView === 'user-insights'" class="page">
        <div class="pageTitle">
          <div>
            <h1>用户洞察</h1>
            <p>基于偏好、对话和行为更新长期画像。</p>
          </div>
        </div>
        <p v-if="adminError" class="inlineError">{{ adminError }}</p>
        <div class="tableList">
          <article v-for="item in insights" :key="item.user_id" class="insightRow">
            <strong>{{ item.display_name }}</strong>
            <span>{{ item.account_id }}</span>
            <span>{{ item.summary || "暂无摘要" }}</span>
            <span>交互 {{ item.interaction_frequency }}</span>
          </article>
        </div>
      </section>

      <section v-if="currentView === 'memory'" class="page">
        <div class="pageTitle">
          <div>
            <h1>记忆档案</h1>
            <p>以用户为单位维护短期记忆、长期记忆、偏好、负向偏好和经营需求。</p>
          </div>
          <button class="ghostButton" :disabled="memoryLoading" @click="loadMemoryModule">刷新</button>
        </div>
        <p v-if="memoryError" class="inlineError">{{ memoryError }}</p>
        <p v-if="memoryStatus" class="inlineSuccess">{{ memoryStatus }}</p>
        <div class="memoryGrid">
          <aside class="memoryUserList">
            <button
              v-for="item in insights"
              :key="item.user_id"
              type="button"
              :class="selectedMemoryUserId === item.user_id ? 'memoryUser active' : 'memoryUser'"
              @click="selectMemoryUser(item.user_id)"
            >
              <strong>{{ item.display_name }}</strong>
              <span>{{ item.account_id }}</span>
            </button>
            <div v-if="!insights.length" class="historyEmpty">暂无用户数据。</div>
          </aside>

          <form class="memoryEditor" @submit.prevent="saveMemory">
            <div class="memoryEditorHeader">
              <div>
                <strong>{{ selectedMemoryUser?.display_name || "请选择用户" }}</strong>
                <span>{{ activeMemory ? "记忆档案已加载" : "尚未加载记忆" }}</span>
              </div>
              <button class="ghostButton" type="button" :disabled="!selectedMemoryUserId || memorySaving" @click="summarizeSelectedMemory">
                生成长期记忆
              </button>
            </div>

            <label>短期记忆摘要<textarea v-model="memoryDraft.short_term_summary" /></label>
            <label>长期记忆摘要<textarea v-model="memoryDraft.long_term_summary" /></label>
            <label>用户偏好 JSON<textarea v-model="memoryDraft.preferences_json" /></label>
            <label>负向偏好<textarea v-model="memoryDraft.negative_preferences_text" placeholder="每行一条" /></label>
            <label>经营需求<textarea v-model="memoryDraft.business_needs_text" placeholder="每行一条" /></label>
            <label>行为记录<textarea v-model="memoryDraft.behavior_notes_text" placeholder="每行一条" /></label>
            <label>召回信号 JSON<textarea v-model="memoryDraft.recall_signals_json" /></label>
            <label>标签<input v-model="memoryDraft.tags_text" placeholder="美妆个护, 小红书, 低客单价" /></label>
            <button class="primaryButton" :disabled="!selectedMemoryUserId || memorySaving">
              {{ memorySaving ? "保存中" : "保存记忆档案" }}
            </button>
          </form>
        </div>
      </section>

      <section v-if="currentView === 'rag'" class="page">
        <div class="pageTitle">
          <div>
            <h1>知识库</h1>
            <p>上传内部资料，系统会切分、索引，并作为 Agent 的检索工具。</p>
          </div>
          <button class="ghostButton" :disabled="ragLoading" @click="loadRagDocuments">刷新</button>
        </div>
        <p v-if="ragError" class="inlineError">{{ ragError }}</p>
        <p v-if="ragStatus" class="inlineSuccess">{{ ragStatus }}</p>
        <div class="ragGrid">
          <form class="sideForm" @submit.prevent="uploadRagDocument">
            <h2>上传文档</h2>
            <label>
              类目
              <select v-model="ragCategory">
                <option v-for="item in ragCategories" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label>
              文件
              <input class="fileInput" type="file" accept=".txt,.md,.csv,.json" @change="selectRagFile" />
            </label>
            <button class="primaryButton" :disabled="ragLoading || !ragFile">
              {{ ragLoading ? "处理中" : "上传并索引" }}
            </button>
          </form>

          <div class="ragMain">
            <section class="ragSearchPanel">
              <form class="ragSearchForm" @submit.prevent="searchRagDocuments">
                <input v-model="ragQuery" placeholder="搜索内部知识库" />
                <select v-model="ragSearchCategory">
                  <option value="">全部类目</option>
                  <option v-for="item in ragCategories" :key="item" :value="item">{{ item }}</option>
                </select>
                <button class="primaryButton" :disabled="ragLoading">检索</button>
              </form>
              <div v-if="ragResults.length" class="ragSearchResults">
                <article v-for="(item, index) in ragResults" :key="`${item.metadata.document_id}-${item.metadata.chunk_index}-${index}`" class="ragResultCard">
                  <div class="trendHeader">
                    <strong>{{ item.metadata.filename || "知识片段" }}</strong>
                    <span>{{ Math.round(item.score * 100) }}分</span>
                  </div>
                  <p>{{ item.text }}</p>
                  <div class="tagRow">
                    <span>{{ item.metadata.category || "未分类" }}</span>
                    <span>分块 {{ item.metadata.chunk_index ?? index }}</span>
                  </div>
                </article>
              </div>
              <div v-else class="emptyState compactEmpty">暂无检索结果。</div>
            </section>

            <section class="ragDocuments">
              <div class="listHeader">
                <strong>文档列表</strong>
                <span>{{ ragDocuments.length }} 份文档</span>
              </div>
              <article v-for="item in ragDocuments" :key="item.id" class="trendCard">
                <div class="trendHeader">
                  <strong>{{ item.filename }}</strong>
                  <span>{{ item.vectorized ? `${item.chunk_count}块` : "未索引" }}</span>
                </div>
                <div class="tagRow">
                  <span>{{ item.category }}</span>
                  <span>{{ item.visibility }}</span>
                  <span>{{ item.created_at.slice(0, 10) }}</span>
                </div>
                <div class="docActions">
                  <button class="ghostButton" type="button" :disabled="ragIndexingId === item.id" @click="reindexRagDocument(item)">
                    {{ ragIndexingId === item.id ? "索引中" : "重建索引" }}
                  </button>
                  <button class="dangerButton" type="button" :disabled="ragDeletingId === item.id" @click="deleteRagDocument(item)">
                    {{ ragDeletingId === item.id ? "删除中" : "删除" }}
                  </button>
                </div>
              </article>
              <div v-if="!ragDocuments.length" class="emptyState compactEmpty">暂无文档。</div>
            </section>
          </div>
        </div>
      </section>

      <section v-if="currentView === 'recall'" class="page">
        <div class="pageTitle">
          <div>
            <h1>一键召回</h1>
            <p>先刷新候选用户，再为单个用户生成可复制的召回文案。</p>
          </div>
          <button class="ghostButton" type="button" @click="loadRecall">刷新候选</button>
        </div>
        <p v-if="adminError" class="inlineError">{{ adminError }}</p>
        <div v-if="!recallItems.length" class="emptyState">暂无可召回用户。可以先用普通账号对话几轮，再回到这里刷新候选。</div>
        <div class="recallGrid">
          <article v-for="item in recallItems" :key="item.user_id" class="trendCard">
            <div class="trendHeader">
              <strong>{{ item.display_name }}</strong>
              <span>召回 {{ Math.round(item.recall_score * 100) }}分</span>
            </div>
            <p>{{ item.reason }}</p>
            <div class="tagRow">
              <span>{{ item.account_id }}</span>
              <span v-for="tag in item.preferred_categories" :key="tag">{{ tag }}</span>
              <span v-for="trend in item.matched_trends" :key="trend">匹配 {{ trend }}</span>
            </div>
            <button class="primaryButton" :disabled="recallGeneratingUserId === item.user_id" @click="generateRecall(item.user_id)">
              {{ recallGeneratingUserId === item.user_id ? "生成中" : "生成召回文案" }}
            </button>
          </article>
        </div>
      </section>
    </main>

    <div v-if="authOpen && !user" class="modalLayer">
      <div class="authPanel">
        <button class="ghostIcon closeButton" aria-label="关闭登录提示" @click="closeAuth">×</button>
        <div class="authTabs">
          <button :class="authMode === 'login' ? 'active' : ''" @click="authMode = 'login'">登录</button>
          <button :class="authMode === 'register' ? 'active' : ''" @click="authMode = 'register'">注册</button>
        </div>
        <form class="formStack" @submit.prevent="submitAuth">
          <label v-if="authMode === 'login'">账号或用户名<input v-model="identifier" required /></label>
          <template v-else>
            <label>名字<input v-model="displayName" required /></label>
            <label>偏好领域<input v-model="categoriesText" /></label>
            <label>常关注平台<input v-model="platformsText" /></label>
            <label>主要经营方向<input v-model="businessFocus" /></label>
            <label>Admin 邀请码<input v-model="adminCode" /></label>
          </template>
          <label>密码<input v-model="password" type="password" required minlength="6" /></label>
          <p v-if="authError" class="formError">{{ authError }}</p>
          <button class="primaryButton" type="submit">{{ authMode === "login" ? "进入工作台" : "创建账号" }}</button>
        </form>
      </div>
    </div>

    <div v-if="recallMessage" class="modalLayer">
      <div class="messageDialog">
        <h2>召回文案</h2>
        <p>{{ recallMessage }}</p>
        <div class="dialogActions">
          <button class="ghostButton" @click="copyRecallMessage">复制</button>
          <button class="primaryButton" @click="recallMessage = ''">完成</button>
        </div>
      </div>
    </div>
  </div>
</template>
