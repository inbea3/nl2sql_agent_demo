# LLM 实现：查询计划
from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from models.llm import build_chat_model
from prompts.query_planner_prompt import QUERY_PLANNER_PROMPT_TEMPLATE

llm = build_chat_model(temperature=0.1, max_tokens=700)


def _generate_query_plan_impl(user_input: str, subproblems: str, db_schema: Any) -> str:
    db_schema_str = (
        db_schema if isinstance(db_schema, str) else json.dumps(db_schema, ensure_ascii=False)
    )
    prompt = ChatPromptTemplate.from_messages([("user", QUERY_PLANNER_PROMPT_TEMPLATE)])
    chain = prompt | llm
    text = chain.invoke(
        {
            "user_input": user_input,
            "subproblems": subproblems,
            "db_schema": db_schema_str,
        }
    ).content

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return json.dumps(
        {
            "goal": "",
            "tables": [],
            "filters": [],
            "time_bucket": "",
            "group_by": [],
            "metrics": [],
            "order_by": [],
            "steps": [text.strip()],
            "notes": [],
        },
        ensure_ascii=False,
        indent=2,
    )


@tool
def generate_query_plan(user_input: str, subproblems: str, db_schema: Any) -> str:
    """调用 LLM 生成「短 JSON 查询计划」（保留 CoT，但严格限长）。"""
    return _generate_query_plan_impl(user_input, subproblems, db_schema)
