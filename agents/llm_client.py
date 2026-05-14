"""
统一封装大模型接口。

LLMClient 只负责：
1. 从环境变量读取模型配置；
2. 调用大模型；
3. 返回文本或 JSON。

它不负责业务判断，不负责 Agent 编排，不负责数据库存储。
"""

import os
import json
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 加载环境变量
class LLMClient:
    """
    LLMClient是一个封装了OpenAI接口的客户端类，负责大模型的创建功能
    """
    def __init__(
        self,
        api_key: str | None = None,
        api_base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.api_base_url = api_base_url or os.getenv("LLM_BASE_URL")
        self.model = model or os.getenv("LLM_MODEL")
        self.temperature = temperature
        self.timeout_seconds = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "0"))

        self.client = OpenAI(
            api_key=self.api_key, 
            base_url=self.api_base_url,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
            )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_base_url and self.model)
    
    def chat(self, messages: list[dict[str, str]]) -> str:
        """
        调用大模型接口，返回文本或 JSON。
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=2048,
        )

        content = (response.choices[0].message.content or "").strip()
        return content
    
    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        调用大模型接口，返回JSON格式的结果。
        """
        content = self._strip_json_fence(self.chat(messages))
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的内容无法解析为JSON: {content}")

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_executor,
        max_rounds: int = 3,
    ) -> dict[str, Any]:
        """
        Run a small OpenAI-compatible function calling loop.

        tool_executor receives (tool_name, arguments_dict) and returns any JSON-serializable result.
        """

        conversation = [dict(message) for message in messages]
        tool_results: list[dict[str, Any]] = []
        for _ in range(max_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=conversation,
                temperature=self.temperature,
                max_tokens=2048,
                tools=tools,
                tool_choice="auto",
            )
            message = response.choices[0].message
            tool_calls = list(message.tool_calls or [])
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments or "{}",
                        },
                    }
                    for tool_call in tool_calls
                ]
            conversation.append(assistant_message)
            if not tool_calls:
                return {
                    "content": (message.content or "").strip(),
                    "messages": conversation,
                    "tool_results": tool_results,
                }
            for tool_call in tool_calls:
                name = tool_call.function.name
                arguments = self._parse_tool_arguments(tool_call.function.arguments or "{}")
                try:
                    result = tool_executor(name, arguments)
                except Exception as exc:
                    result = {"error": str(exc)}
                tool_results.append({"name": name, "arguments": arguments, "result": result})
                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        return {"content": "", "messages": conversation, "tool_results": tool_results}

    @staticmethod
    def _strip_json_fence(content: str) -> str:
        text = content.strip()
        if text.startswith("```json"):
            text = text.removeprefix("```json").strip()
        elif text.startswith("```"):
            text = text.removeprefix("```").strip()
        if text.endswith("```"):
            text = text.removesuffix("```").strip()
        return text

    @staticmethod
    def _parse_tool_arguments(content: str) -> dict[str, Any]:
        try:
            value = json.loads(content or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}
