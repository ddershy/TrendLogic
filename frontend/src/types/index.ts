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
  type: "process" | "final";
  agent: string;
  function?: string | null;
  content: string;
}

export interface ChatResponse {
  session_id: string;
  messages: AgentMessage[];
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  message_count: number;
  last_message_at: string | null;
  preview: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionHistory extends ChatSessionSummary {
  user_transcript: string;
  assistant_transcript: string;
  session_summary: string;
  trace_summary: string;
  recent_interactions: Array<Record<string, unknown>>;
}

export interface MemoryContext {
  user_id: string;
  session_id: string | null;
  user_profile_summary: string;
  short_term_summary: string;
  short_messages: Record<string, unknown>;
  long_term_summary: string;
  session_summary: string;
  recent_user_transcript: string;
  preferences: string[];
  negative_preferences: string[];
  business_needs: string[];
  recall_signals: string[];
  tags: string[];
  metadata: Record<string, unknown>;
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

export interface UserMemoryProfile {
  id: string;
  user_id: string;
  short_messages: Record<string, unknown>;
  short_term_summary: string;
  long_term_summary: string;
  preferences: Record<string, unknown>;
  negative_preferences: string[];
  business_needs: string[];
  behavior_notes: string[];
  recall_signals: Array<Record<string, unknown>>;
  tags: string[];
  confidence: number;
  last_used_at: string | null;
  created_at: string;
  updated_at: string;
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
