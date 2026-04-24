# LLM 实现：SQL 纠错
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from models.llm import build_chat_model
from prompts.error_corrector_prompt import ERROR_CORRECTOR_PROMPT_TEMPLATE

llm = build_chat_model(temperature=0.1)

_SQL_FENCE_RE = re.compile(
    r"```(?:sql|postgresql)?\s*([\s\S]*?)\s*```", re.IGNORECASE
)
_SQL_STMT_RE = re.compile(r"(?is)\b(with\b[\s\S]+?\)\s*)?select\b[\s\S]+?(?:;|\Z)")


def _extract_sql(text: str) -> str:
    if not text:
        return ""
    s = str(text).strip()
    m = _SQL_FENCE_RE.search(s)
    if m:
        return (m.group(1) or "").strip()
    m2 = _SQL_STMT_RE.search(s)
    if m2:
        return (m2.group(0) or "").strip()
    return s


def _correct_sql_impl(user_input: str, original_sql: str, error_msg: str, schema: Any) -> str:
    schema_str = schema if isinstance(schema, str) else json.dumps(schema, ensure_ascii=False)
    prompt = ChatPromptTemplate.from_messages([("user", ERROR_CORRECTOR_PROMPT_TEMPLATE)])
    chain = prompt | llm
    raw = chain.invoke(
        {
            "user_input": user_input,
            "error_msg": error_msg,
            "original_sql": original_sql,
            "schema": schema_str,
        }
    ).content
    sql = _extract_sql(raw)
    sql = (
        str(sql)
        .replace("```sql", "")
        .replace("```postgresql", "")
        .replace("```", "")
        .strip()
    )
    return sql


@tool
def correct_sql(user_input: str, original_sql: str, error_msg: str, schema: Any) -> str:
    """根据执行错误信息、原 SQL 与库表结构，让 LLM 生成修正后的 SQL 文本。"""
    return _correct_sql_impl(user_input, original_sql, error_msg, schema)
