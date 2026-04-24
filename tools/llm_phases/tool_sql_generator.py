# LLM 实现：SQL 生成（供 skill_sql 等调用）
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from models.llm import build_chat_model
from prompts.sql_generator_prompt import SQL_GENERATION_PROMPT_TEMPLATE

llm = build_chat_model(temperature=0.1)

_SQL_FENCE_RE = re.compile(
    r"```(?:sql|postgresql)?\s*([\s\S]*?)\s*```", re.IGNORECASE
)
_SQL_STMT_RE = re.compile(r"(?is)\b(with\b[\s\S]+?\)\s*)?select\b[\s\S]+?(?:;|\Z)")


def _extract_sql(text: str) -> str:
    if not text:
        return ""
    m = _SQL_FENCE_RE.search(text)
    if m:
        return (m.group(1) or "").strip()
    m2 = _SQL_STMT_RE.search(text)
    if m2:
        return (m2.group(0) or "").strip()
    return text.strip()


def _generate_sql_impl(plan: Any, schema: Any) -> str:
    is_dsl = isinstance(plan, dict)

    plan_str = plan
    if is_dsl and not isinstance(plan, str):
        plan_str = json.dumps(plan, ensure_ascii=False)
    if not isinstance(plan_str, str):
        plan_str = str(plan_str)

    schema_str = schema if isinstance(schema, str) else json.dumps(schema, ensure_ascii=False)

    prompt = ChatPromptTemplate.from_messages([("user", SQL_GENERATION_PROMPT_TEMPLATE)])
    chain = prompt | llm
    raw = chain.invoke(
        {
            "input_type": "DSL" if is_dsl else "计划",
            "plan": plan_str,
            "schema": schema_str,
        }
    ).content
    sql = _extract_sql(raw)
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


@tool
def generate_sql(plan: Any, schema: Any) -> str:
    """根据查询计划或 DSL 与表结构让 LLM 生成 PostgreSQL。"""
    return _generate_sql_impl(plan, schema)
