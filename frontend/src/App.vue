<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { api, setToken } from "./api/client";
import type { AgentMessage, RecallCandidate, TrendingItem, User, UserInsight } from "./types";

type ViewName = "chat" | "trending" | "user-insights" | "recall";
type AuthMode = "login" | "register";

interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  trace?: AgentMessage;
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
const chatError = ref("");
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
const trendError = ref("");

const insights = ref<UserInsight[]>([]);
const recallItems = ref<RecallCandidate[]>([]);
const recallMessage = ref("");
const adminError = ref("");

const navItems = computed(() => [
  { key: "chat" as const, label: "智能运营台", adminOnly: false },
  { key: "trending" as const, label: "最新爆品", adminOnly: false },
  { key: "user-insights" as const, label: "用户洞察", adminOnly: true },
  { key: "recall" as const, label: "一键召回", adminOnly: true }
]);

const visibleNavItems = computed(() => navItems.value.filter((item) => !item.adminOnly || user.value?.role === "admin"));
const visibleChatEntries = computed(() =>
  chatLoading.value
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

onMounted(async () => {
  try {
    user.value = await api.me();
    authOpen.value = false;
    await loadTrending();
  } catch {
    setToken(null);
  }
});

watch([visibleChatEntries, openTraceGroups], async () => {
  await nextTick();
  messageBottom.value?.scrollIntoView({ behavior: "smooth", block: "end" });
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
    await loadTrending();
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
}

async function sendMessage() {
  if (!chatText.value.trim() || !user.value) return;
  const text = chatText.value.trim();
  chatText.value = "";
  chatError.value = "";
  chatEntries.value.push({ id: crypto.randomUUID(), role: "user", content: text });
  chatLoading.value = true;
  try {
    const response = await api.sendMessage(text, sessionId.value);
    sessionId.value = response.session_id;
    for (const message of response.messages) {
      chatEntries.value.push(
        message.type === "process"
          ? { id: crypto.randomUUID(), role: "assistant", content: message.content, trace: message }
          : { id: crypto.randomUUID(), role: "assistant", content: message.content }
      );
    }
  } catch (error) {
    chatError.value = error instanceof Error ? error.message : "发送失败";
  } finally {
    chatLoading.value = false;
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

async function loadInsights() {
  if (user.value?.role !== "admin") return;
  adminError.value = "";
  try {
    insights.value = await api.userInsights();
  } catch (error) {
    adminError.value = error instanceof Error ? error.message : "加载失败";
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

async function switchView(view: ViewName) {
  currentView.value = view;
  if (view === "trending") await loadTrending();
  if (view === "user-insights") await loadInsights();
  if (view === "recall") await loadRecall();
}

async function generateRecall(userId: string) {
  try {
    const result = await api.generateRecall(userId);
    recallMessage.value = result.message;
  } catch (error) {
    adminError.value = error instanceof Error ? error.message : "生成失败";
  }
}

function copyRecallMessage() {
  navigator.clipboard.writeText(recallMessage.value);
}

function splitTags(value: string) {
  return value
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
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
                <div class="bubble">{{ item.entry.content }}</div>
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
                <span>热度指数 {{ Math.round(item.heat_score * 100) }}分</span>
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

      <section v-if="currentView === 'recall'" class="page">
        <div class="pageTitle">
          <div>
            <h1>一键召回</h1>
            <p>根据用户画像、活跃度和近期爆品生成召回文案。</p>
          </div>
        </div>
        <p v-if="adminError" class="inlineError">{{ adminError }}</p>
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
            </div>
            <button class="primaryButton" @click="generateRecall(item.user_id)">生成召回口令</button>
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
