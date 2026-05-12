import type {
  AuthResponse,
  ChatResponse,
  ChatSessionHistory,
  ChatSessionSummary,
  RecallCandidate,
  TrendingItem,
  User,
  UserInsight
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
  listChatSessions: () => request<ChatSessionSummary[]>("/chat/sessions"),
  getChatHistory: (session_id: string) =>
    request<ChatSessionHistory>(`/chat/history?session_id=${encodeURIComponent(session_id)}`),
  createChatSession: () =>
    request<ChatSessionSummary>("/chat/session", {
      method: "POST",
      body: JSON.stringify({})
    }),
  listTrending: () => request<TrendingItem[]>("/trending"),
  listTrendingCategories: () => request<string[]>("/trending/categories"),
  createTrending: (payload: Partial<TrendingItem>) =>
    request<TrendingItem>("/trending", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  userInsights: () => request<UserInsight[]>("/admin/user-insights"),
  recallCandidates: () => request<RecallCandidate[]>("/recall/candidates"),
  generateRecall: (user_id: string) =>
    request<{ message: string; recall_score: number; matched_trends: string[]; reason: string }>("/recall/generate", {
      method: "POST",
      body: JSON.stringify({ user_id })
    })
};
