# LLM 实现：Schema 关联
from __future__ import annotations

import json
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from constraint.schema_linking_constraint import TableRetrievalOutput
from models.llm import build_chat_model
from prompts.schema_linker_prompt import SCHEMA_LINKING_SYSTEM_PROMPT_TEMPLATE

llm = build_chat_model(temperature=0.1)


def _schema_linking_impl(user_input: str, all_db: dict[str, Any]) -> list[str]:
    parser = PydanticOutputParser(pydantic_object=TableRetrievalOutput)
    fmt = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SCHEMA_LINKING_SYSTEM_PROMPT_TEMPLATE),
            ("user", "{question}"),
        ]
    )
    chain = prompt | llm | parser
    schema_str = json.dumps(all_db, ensure_ascii=False)
    return chain.invoke(
        {"schema": schema_str, "question": user_input, "format_instructions": fmt}
    ).tables


@tool
def schema_linking(user_input: str, all_db: dict[str, Any]) -> list[str]:
    """根据用户问题从完整库结构中检索最相关的表名列表（Pydantic 解析）。"""
    return _schema_linking_impl(user_input, all_db)
