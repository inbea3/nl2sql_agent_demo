# LLM 实现：子问题分解
from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from models.llm import build_chat_model
from prompts.subproblem_decomposer_prompt import SUBPROBLEM_DECOMPOSER_PROMPT_TEMPLATE

llm = build_chat_model(temperature=0.1)


def _decompose_subproblem_impl(user_input: str, filtered_schema: Any) -> str:
    schema_str = (
        filtered_schema
        if isinstance(filtered_schema, str)
        else json.dumps(filtered_schema, ensure_ascii=False)
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("user", SUBPROBLEM_DECOMPOSER_PROMPT_TEMPLATE),
        ]
    )
    chain = prompt | llm
    return chain.invoke(
        {
            "user_input": user_input,
            "schema": schema_str,
        }
    ).content


@tool
def decompose_subproblem(user_input: str, filtered_schema: Any) -> str:
    """将用户问题按（已过滤的）schema 上下文拆解为若干可独立执行的子问题描述。"""
    return _decompose_subproblem_impl(user_input, filtered_schema)
