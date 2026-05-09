import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../stores/auth";
import type { UserInsight } from "../types";

export default function UserInsightsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<UserInsight[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (user?.role !== "admin") return;
    api.userInsights().then(setItems).catch((err) => setError(err instanceof Error ? err.message : "加载失败"));
  }, [user]);

  if (user?.role !== "admin") {
    return <section className="page"><div className="emptyState">仅 admin 可访问用户洞察。</div></section>;
  }

  return (
    <section className="page">
      <div className="pageTitle">
        <div>
          <h1>用户洞察</h1>
          <p>基于偏好、对话和行为更新长期画像。</p>
        </div>
      </div>
      {error ? <p className="inlineError">{error}</p> : null}
      <div className="tableList">
        {items.map((item) => (
          <article className="insightRow" key={item.user_id}>
            <strong>{item.display_name}</strong>
            <span>{item.account_id}</span>
            <span>{item.summary || "暂无摘要"}</span>
            <span>交互 {item.interaction_frequency}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
