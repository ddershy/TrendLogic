from __future__ import annotations

import os

from agents.llm_client import LLMClient

from .prompts import SHORT_TERM_SUMMARY_PROMPT


class MemorySummarizer:
    """Compresses short-term dialogue memory."""

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        try:
            self.llm_client = llm_client or LLMClient(model=os.getenv("MEMORY_MODEL") or None)
        except Exception:
            self.llm_client = None

    def summarize(self, existing_summary: str, older_interactions: list[dict]) -> str:
        if not older_interactions:
            return existing_summary

        text = "\n".join(
            f"用户：{item.get('user_message', '')}\n助手：{item.get('assistant_message', '')}"
            for item in older_interactions
        )
        if self.llm_client and self.llm_client.is_configured:
            try:
                return self.llm_client.chat(
                    [
                        {"role": "system", "content": SHORT_TERM_SUMMARY_PROMPT},
                        {
                            "role": "user",
                            "content": f"已有摘要：{existing_summary or '暂无'}\n\n需要压缩的较早对话：\n{text}",
                        },
                    ]
                )[:1200]
            except Exception:
                pass

        fallback = text.replace("\n", "；")
        if existing_summary:
            fallback = f"{existing_summary}；{fallback}"
        return fallback[-1200:]
