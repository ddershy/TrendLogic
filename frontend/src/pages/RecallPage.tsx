import { useEffect, useState } from "react";
import { Copy, Wand2 } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../stores/auth";
import type { RecallCandidate } from "../types";

export default function RecallPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<RecallCandidate[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.role !== "admin") return;
    api.recallCandidates().then(setItems).catch((err) => setError(err instanceof Error ? err.message : "加载失败"));
  }, [user]);

  if (user?.role !== "admin") {
    return <section className="page"><div className="emptyState">仅 admin 可访问一键召回。</div></section>;
  }

  async function generate(userId: string) {
    try {
      const result = await api.generateRecall(userId);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    }
  }

  return (
    <section className="page">
      <div className="pageTitle">
        <div>
          <h1>一键召回</h1>
          <p>根据用户画像、活跃度和近期爆品生成召回文案。</p>
        </div>
      </div>
      {error ? <p className="inlineError">{error}</p> : null}
      <div className="recallGrid">
        {items.map((item) => (
          <article className="trendCard" key={item.user_id}>
            <div className="trendHeader">
              <strong>{item.display_name}</strong>
              <span>{Math.round(item.recall_score * 100)}</span>
            </div>
            <p>{item.reason}</p>
            <div className="tagRow">
              <span>{item.account_id}</span>
              {item.preferred_categories.map((tag) => <span key={tag}>{tag}</span>)}
            </div>
            <button className="primaryButton" onClick={() => generate(item.user_id)}>
              <Wand2 size={16} /> 生成召回口令
            </button>
          </article>
        ))}
      </div>
      {message ? (
        <div className="modalLayer">
          <div className="messageDialog">
            <h2>召回文案</h2>
            <p>{message}</p>
            <div className="dialogActions">
              <button className="ghostButton" onClick={() => navigator.clipboard.writeText(message)}>
                <Copy size={16} /> 复制
              </button>
              <button className="primaryButton" onClick={() => setMessage("")}>完成</button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
