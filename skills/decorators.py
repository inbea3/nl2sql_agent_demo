"""Agent 侧「技能」装饰器：语义上与 LangChain `tool` 区分，实现上等价于注册为可调工具。"""
from __future__ import annotations

from langchain_core.tools import tool as skill

__all__ = ["skill"]
