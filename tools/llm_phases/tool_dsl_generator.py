# LLM 实现：DSL 生成
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from constraint.dsl_constraint import DSLOutput
from domain.risk_metrics import METRIC_DICTION_PROMPT
from models.llm import build_chat_model
from prompts.dsl_generator_prompt import (
    DSL_FIELD_OP_VALUE_HINT_TEMPLATE,
    DSL_GENERATOR_SYSTEM_PROMPT_TEMPLATE,
    DSL_GENERATOR_USER_PROMPT_TEMPLATE,
    DSL_NO_HARD_CONSTRAINTS_HINT,
    DSL_RANGE_HINT_TEMPLATE,
    DSL_TIME_GRAIN_HINT_TEMPLATE,
)

llm = build_chat_model(temperature=0.1)

_CMP_WORDS = {
    "大于等于": "gte",
    "不少于": "gte",
    "不小于": "gte",
    ">= ": "gte",
    ">=": "gte",
    "小于等于": "lte",
    "不超过": "lte",
    "不大于": "lte",
    "<= ": "lte",
    "<=": "lte",
    "大于": "gt",
    "> ": "gt",
    ">": "gt",
    "小于": "lt",
    "< ": "lt",
    "<": "lt",
    "不等于": "ne",
    "不为": "ne",
    "≠": "ne",
    "等于": "eq",
    "为": "eq",
    "是": "eq",
    "=": "eq",
    "包含": "like",
    "含": "like",
}

_TIME_GRAIN_PATTERNS = [
    (re.compile(r"(按|按照).{0,10}(年份|年|年度)"), "year"),
    (re.compile(r"(按|按照).{0,10}(季度|季)"), "quarter"),
    (re.compile(r"(按|按照).{0,10}(月份|月|月度)|按月|每月|月度|月份"), "month"),
    (re.compile(r"(按|按照).{0,10}(周|周度)|按周|每周"), "week"),
    (re.compile(r"(按|按照).{0,10}(日期|日|天|日度)|按日|每日"), "day"),
]

_RANGE_RE = re.compile(r"(?:在|介于|从)\s*([^\s，,。；;]+)\s*(?:到|至|~|－|-)\s*([^\s，,。；;]+)")
_FIELD_OP_VALUE_RE = re.compile(
    r"(?P<field>[\u4e00-\u9fa5A-Za-z0-9_\.]{1,30})\s*(?P<op>不等于|不为|大于等于|小于等于|不少于|不超过|大于|小于|等于|为|是|>=|<=|>|<|=|包含|含)\s*(?P<value>[^\s，,。；;\n]+)"
)


def _extract_hard_constraints(user_input: str) -> str:
    if not user_input:
        return ""
    s = str(user_input).strip()
    if not s:
        return ""

    hints: list[str] = []

    for pat, grain in _TIME_GRAIN_PATTERNS:
        if pat.search(s):
            hints.append(DSL_TIME_GRAIN_HINT_TEMPLATE.format(grain=grain))
            break

    m_range = _RANGE_RE.search(s)
    if m_range:
        a, b = (m_range.group(1) or "").strip(), (m_range.group(2) or "").strip()
        if a and b:
            hints.append(DSL_RANGE_HINT_TEMPLATE.format(a=a, b=b))

    for m in _FIELD_OP_VALUE_RE.finditer(s):
        field = (m.group("field") or "").strip()
        op_raw = (m.group("op") or "").strip()
        value = (m.group("value") or "").strip()
        op = _CMP_WORDS.get(op_raw, "")
        if not (field and op and value):
            continue
        if len(field) <= 1:
            continue
        hints.append(
            DSL_FIELD_OP_VALUE_HINT_TEMPLATE.format(field=field, op=op, value=value)
        )

    seen = set()
    out: list[str] = []
    for h in hints:
        if h in seen:
            continue
        seen.add(h)
        out.append(h)
    return "\n".join(out).strip()


def _generate_dsl_impl(user_input: str, schema: Any) -> dict[str, Any]:
    parser = PydanticOutputParser(pydantic_object=DSLOutput)
    fmt = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", DSL_GENERATOR_SYSTEM_PROMPT_TEMPLATE),
            ("user", DSL_GENERATOR_USER_PROMPT_TEMPLATE),
        ]
    )

    schema_str = schema if isinstance(schema, str) else json.dumps(schema, ensure_ascii=False)
    chain = prompt | llm | parser
    hard_constraints = _extract_hard_constraints(str(user_input))
    return chain.invoke(
        {
            "format_instructions": fmt,
            "metric_dict": METRIC_DICTION_PROMPT,
            "schema": schema_str,
            "question": user_input,
            "hard_constraints": hard_constraints or DSL_NO_HARD_CONSTRAINTS_HINT,
        }
    ).dict()


@tool
def generate_dsl(user_input: str, schema: Any) -> dict[str, Any]:
    """结合指标词典与用户问题，让 LLM 输出符合 DSLOutput 的结构化 DSL 字典。"""
    return _generate_dsl_impl(user_input, schema)
