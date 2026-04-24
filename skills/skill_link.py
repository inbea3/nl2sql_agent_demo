from __future__ import annotations

from skills.decorators import skill
from tools.db.tool_schema_store import _load_database_schema_impl
from tools.llm_phases.tool_schema_linker import _schema_linking_impl


@skill
def schema_linking_tool(user_input: str):
    """从全库 Schema 中识别与用户问题强相关的表名列表（list[str]）。

    何时调用：已完成或已掌握全库 schema 后，需要把问题聚焦到少数相关表时；通常在 discover_schema_tool 之后。
    输入：与业务一致的完整自然语言问题（可与用户原文相同）。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    return _schema_linking_impl(user_input, all_db)
