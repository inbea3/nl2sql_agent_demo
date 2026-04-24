from __future__ import annotations

from skills.decorators import skill
from tools.db.tool_schema_store import _filter_schema_by_tables_impl, _load_database_schema_impl
from tools.llm_phases.tool_subproblem_decomposer import _decompose_subproblem_impl


@skill
def subproblem_decompose_tool(user_input: str, tables: list):
    """在「相关表」对应的过滤后 schema 上，将复杂问题拆成多条可独立执行的子问题（str）。

    何时调用：在 schema_linking_tool 得到 tables 之后；多指标/多步统计时必须调用。
    参数 tables：与 schema_linking_tool 输出一致的相关表名列表。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    filtered_schema = _filter_schema_by_tables_impl(all_db, tables)
    filtered_schema["schema"] = "public"
    return _decompose_subproblem_impl(user_input, filtered_schema)
