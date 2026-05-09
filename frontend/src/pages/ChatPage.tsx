import { FormEvent, useMemo, useState } from "react";
import { SendHorizontal } from "lucide-react";
import { api } from "../api/client";
import MessageList, { ChatEntry } from "../components/chat/MessageList";
import { useAuth } from "../stores/auth";
import { useChatStore } from "../stores/chat";

export default function ChatPage() {
  const { user } = useAuth();
  const { entries, setEntries, sessionId, setSessionId } = useChatStore();
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const visibleEntries = useMemo(
    () =>
      loading
        ? [
            ...entries,
            {
              id: "pending-analysis",
              role: "assistant" as const,
              content: "我正在整理你的问题，先判断它属于哪个运营场景，再决定是否需要补充关键信息。"
            }
          ]
        : entries,
    [entries, loading]
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim() || !user) return;
    const userText = content.trim();
    setContent("");
    setError("");
    setEntries((current) => [...current, { id: crypto.randomUUID(), role: "user", content: userText }]);
    setLoading(true);
    try {
      const response = await api.sendMessage(userText, sessionId);
      setSessionId(response.session_id);
      setEntries((current) => [
        ...current,
        ...response.messages.map((message) =>
          message.type === "trace"
            ? { id: crypto.randomUUID(), role: "assistant" as const, content: message.content, trace: message }
            : { id: crypto.randomUUID(), role: "assistant" as const, content: message.content }
        )
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page chatPage">
      <div className="pageTitle">
        <div>
          <h1>智能运营台</h1>
          <p>输入平台、类目、预算或运营目标，系统会路由到合适的 Agent。</p>
        </div>
      </div>
      <div className="chatSurface">
        {entries.length ? (
          <MessageList entries={visibleEntries} />
        ) : (
          <div className="emptyState">可以试试：“我想在小红书做美妆选品，预算 5000 元，适合卖什么？”</div>
        )}
        <form className="composer" onSubmit={submit}>
          <input
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={!user || loading}
            placeholder={user ? "描述你的选品、流量或带货问题" : "请先登录"}
          />
          <button type="submit" className="primaryIconButton" disabled={!user || loading} aria-label="发送">
            <SendHorizontal size={18} />
          </button>
        </form>
        {error ? <p className="inlineError">{error}</p> : null}
      </div>
    </section>
  );
}
