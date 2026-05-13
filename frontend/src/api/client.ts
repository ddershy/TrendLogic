import type {
  AgentMessage,
  AuthResponse,
  ChatResponse,
  ChatSessionHistory,
  ChatSessionSummary,
  MemoryContext,
  RecallCandidate,
  TrendingItem,
  User,
  UserInsight,
  UserMemoryProfile
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken() {
  return localStorage.getItem("trendlogic_token");
}

export function setToken(token: string | null) {
  if (token) {
    localStorage.setItem("trendlogic_token", token);
  } else {
    localStorage.removeItem("trendlogic_token");
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, body.detail ?? "请求失败");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export type ChatStreamEvent =
  | { event: "session"; session_id: string }
  | { event: "process"; message: AgentMessage }
  | { event: "final_start"; message: AgentMessage }
  | { event: "final_delta"; content: string }
  | { event: "done"; session_id: string };

async function requestStream(path: string, body: unknown, onEvent: (event: ChatStreamEvent) => void) {
  const token = getToken();
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body)
  });
  if (!response.ok || !response.body) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorBody.detail ?? "请求失败");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const text = line.trim();
      if (text) {
        onEvent(JSON.parse(text) as ChatStreamEvent);
      }
    }
  }
  const tail = buffer.trim();
  if (tail) {
    onEvent(JSON.parse(tail) as ChatStreamEvent);
  }
}

export const api = {
  me: () => request<User>("/auth/me"),
  login: (identifier: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password })
    }),
  register: (payload: {
    display_name: string;
    password: string;
    preferred_categories: string[];
    preferred_platforms: string[];
    business_focus?: string;
    admin_invite_code?: string;
  }) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  sendMessage: (content: string, session_id?: string | null) =>
    request<ChatResponse>("/chat/message", {
      method: "POST",
      body: JSON.stringify({ content, session_id })
    }),
  sendMessageStream: (content: string, session_id: string | null | undefined, onEvent: (event: ChatStreamEvent) => void) =>
    requestStream("/chat/message/stream", { content, session_id }, onEvent),
  listChatSessions: () => request<ChatSessionSummary[]>("/chat/sessions"),
  getChatHistory: (session_id: string) =>
    request<ChatSessionHistory>(`/chat/history?session_id=${encodeURIComponent(session_id)}`),
  createChatSession: () =>
    request<ChatSessionSummary>("/chat/session", {
      method: "POST",
      body: JSON.stringify({})
    }),
  getMemoryContext: (session_id?: string | null) =>
    request<{ memory_context: MemoryContext }>(
      session_id ? `/memory/context?session_id=${encodeURIComponent(session_id)}` : "/memory/context"
    ),
  updateSessionMemory: (session_id: string) =>
    request<{ status: string; memory: UserMemoryProfile; memory_context: MemoryContext; update_plan: Record<string, unknown> }>(
      "/memory/session/update",
      {
        method: "POST",
        body: JSON.stringify({ session_id })
      }
    ),
  listTrending: () => request<TrendingItem[]>("/trending"),
  listTrendingCategories: () => request<string[]>("/trending/categories"),
  createTrending: (payload: Partial<TrendingItem>) =>
    request<TrendingItem>("/trending", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  userInsights: () => request<UserInsight[]>("/admin/user-insights"),
  getUserMemory: (user_id: string) => request<{ user_id: string; memory: UserMemoryProfile }>(`/users/${user_id}/memory`),
  updateUserMemory: (user_id: string, payload: Partial<UserMemoryProfile>) =>
    request<{ user_id: string; memory: UserMemoryProfile }>(`/users/${user_id}/memory`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  summarizeUserMemory: (user_id: string) =>
    request<{ status: string; memory: UserMemoryProfile; profile_update_plan?: Record<string, unknown> }>(
      `/users/${user_id}/memory/summarize`,
      {
      method: "POST",
      body: JSON.stringify({})
      }
    ),
  recallCandidates: () => request<RecallCandidate[]>("/recall/candidates"),
  generateRecall: (user_id: string) =>
    request<{
      message: string;
      recall_score: number;
      matched_trends: string[];
      reason: string;
      recommended_channel?: string;
      timing?: string;
    }>("/recall/generate", {
      method: "POST",
      body: JSON.stringify({ user_id })
    })
};
