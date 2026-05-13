# TrendLogic 指标体系

## 运行时指标

运行时指标会自动写入 `core_metricevent`。

- `rag.search`：RAGService 的真实检索耗时，包含 query embedding 和 LanceDB vector search。
- `rag.endpoint.search`：知识库检索接口耗时。
- `rag.endpoint.answer`：知识库问答接口耗时，包含 RAG 检索和 LLM 生成回答。
- `agent.node`：LangGraph 中单个节点耗时，例如 router、requirement_node、product_consultant。
- `chat.e2e`：聊天接口端到端耗时。流式接口会额外记录 `first_token_ms` 和 `agent_chain_latency_ms`。

admin 汇总接口：

```text
GET /api/admin/metrics/summary
```

## RAG 检索准确率与召回率

RAG 准确率和召回率必须依赖人工标注的评测集，不能从线上日志里凭空计算。

评测用例存储在 `core_ragevaluationcase`：

- `query`：测试问题。
- `expected_document_ids`：期望命中的文档 ID。
- `expected_filenames`：期望命中的文件名。
- `expected_keywords`：如果不方便绑定文档，可以标注期望片段必须包含的关键词。
- `top_k`：本条用例评测的召回条数。

运行评测：

```powershell
backend\.venv\Scripts\python.exe backend\manage.py run_rag_eval --top-k 5
```

结果存储在 `core_ragevaluationrun`：

- `precision_at_k = top_k 结果中相关片段数 / top_k 返回片段数`
- `recall_at_k = top_k 结果中相关片段数 / 标注相关答案数`
- `mrr = 第一个相关结果排名的倒数`
- `avg_latency_ms = 每条评测 query 的平均检索耗时`

## 推理加速比

推理加速比不是单次请求天然存在的指标，需要设定一个 baseline。

建议 baseline：

- 非流式或旧链路端到端耗时：`baseline_ms`
- 当前链路端到端耗时：`current_ms`

公式：

```text
speedup_ratio = baseline_ms / current_ms
```

目前系统已经记录 `chat.e2e`、`agent.node`、`rag.search`，可以用这些数据对比优化前后的平均耗时。

## 迭代方法

1. 先在 admin 后台新增 10-30 条 `RAGEvaluationCase`。
2. 每次改 chunk、embedding、prompt、top_k 或 rerank 逻辑后运行 `run_rag_eval`。
3. 观察 `precision_at_k`、`recall_at_k`、`mrr` 和 `avg_latency_ms`。
4. 同时观察线上 `chat.e2e`、`agent.node`、`rag.search` 是否变慢。
5. 只有当质量指标提升且延迟可接受，才保留这次改动。
