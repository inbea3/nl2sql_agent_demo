from __future__ import annotations

from skills.decorators import skill
from tools.db.tool_schema_store import _filter_schema_by_tables_impl, _load_database_schema_impl
from tools.llm_phases.tool_dsl_generator import _generate_dsl_impl


@skill
def generate_dsl_tool(user_input: str, plan: str, tables: list):
    """生成结构化 DSL（dict，符合 DSLOutput 语义）。

    何时调用：在 query_plan_tool 得到计划之后、生成 SQL 之前；需要把自然语言与计划落到中间表示时。
    参数 plan：query_plan_tool 的返回字符串；tables 用于再次过滤 schema。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    schema = _filter_schema_by_tables_impl(all_db, tables)
    return _generate_dsl_impl(f"{user_input}\n\n查询计划：{plan}", schema)
