export type Role = "normal_user" | "admin";

export interface User {
  id: string;
  account_id: string;
  display_name: string;
  role: Role;
  preferences: Record<string, unknown>;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AgentMessage {
  type: "trace" | "final";
  agent: string;
  function?: string | null;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  messages: AgentMessage[];
}

export interface TrendingItem {
  id: string;
  title: string;
  category: string;
  source: string;
  summary: string;
  heat_score: number;
  tags: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  visibility: "public" | "private_rag_only";
  is_ai_generated: boolean;
}

export interface UserInsight {
  user_id: string;
  display_name: string;
  account_id: string;
  preferred_categories: string[];
  preferred_platforms: string[];
  summary: string;
  interest_weights: Record<string, number>;
  recall_score: number;
  interaction_frequency: number;
  last_active_at: string | null;
}

export interface RecallCandidate {
  user_id: string;
  display_name: string;
  account_id: string;
  last_active_at: string | null;
  preferred_categories: string[];
  recall_score: number;
  reason: string;
}
