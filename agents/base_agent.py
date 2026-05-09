from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentTrace:
    agent: str
    function: str
    content: str


@dataclass
class AgentFinal:
    agent: str
    content: str


class BaseAgent:
    name = "BaseAgent"

    def trace(self, function: str, content: str) -> AgentTrace:
        return AgentTrace(agent=self.name, function=function, content=content)
