import { createContext, useContext, useMemo, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { ChatEntry } from "../components/chat/MessageList";

interface ChatContextValue {
  entries: ChatEntry[];
  setEntries: Dispatch<SetStateAction<ChatEntry[]>>;
  sessionId: string | null;
  setSessionId: Dispatch<SetStateAction<string | null>>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const value = useMemo(() => ({ entries, setEntries, sessionId, setSessionId }), [entries, sessionId]);

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChatStore() {
  const value = useContext(ChatContext);
  if (!value) {
    throw new Error("useChatStore must be used inside ChatProvider");
  }
  return value;
}
