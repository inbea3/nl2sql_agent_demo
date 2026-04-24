from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver


def build_memory() -> MemorySaver:
    return MemorySaver()

