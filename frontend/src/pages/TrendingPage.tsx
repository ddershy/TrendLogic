import { FormEvent, useEffect, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../stores/auth";
import type { TrendingItem } from "../types";

export default function TrendingPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<TrendingItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [summary, setSummary] = useState("");
  const [tags, setTags] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!user) return;
    setError("");
    setRefreshing(true);
    try {
      const [nextItems, nextCategories] = await Promise.all([api.listTrending(), api.listTrendingCategories()]);
      setItems(nextItems);
      setCategories(nextCategories);
      setCategory((current) => current || nextCategories[0] || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => {
    load();
  }, [user]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!user) return;
    try {
      const item = await api.createTrending({
        title,
        category,
        summary,
        source: "user_upload",
        heat_score: 0.7,
        tags: tags.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean),
        visibility: "public",
        is_ai_generated: false
      });
      setItems((current) => [item, ...current]);
      setTitle("");
      setCategory("");
      setSummary("");
      setTags("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "发布失败");
    }
  }

  return (
    <section className="page">
      <div className="pageTitle">
        <div>
          <h1>最新爆品</h1>
          <p>查看公开热点，普通用户可上传公开条目，内部 RAG 文档仅 admin 上传。</p>
        </div>
        <button className="ghostButton" onClick={load} disabled={refreshing}>
          <RefreshCw className={refreshing ? "spinIcon" : ""} size={16} /> {refreshing ? "刷新中" : "刷新"}
        </button>
      </div>
      <div className="contentGrid">
        <form className="sideForm" onSubmit={submit}>
          <h2>上传热点</h2>
          <label>
            标题
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label>
            类目
            <select value={category} onChange={(event) => setCategory(event.target.value)} required>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            摘要
            <textarea value={summary} onChange={(event) => setSummary(event.target.value)} required />
          </label>
          <label>
            标签
            <input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="小红书, 女包" />
          </label>
          <button className="primaryButton" disabled={!user}>
            <Plus size={16} /> 发布
          </button>
        </form>
        <div className="itemList">
          {error ? <p className="inlineError">{error}</p> : null}
          {items.map((item) => (
            <article className="trendCard" key={item.id}>
              <div className="trendHeader">
                <strong>{item.title}</strong>
                <span>热度指数 {Math.round(item.heat_score * 100)}分</span>
              </div>
              <p>{item.summary}</p>
              <div className="tagRow">
                <span>{item.category}</span>
                {item.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
