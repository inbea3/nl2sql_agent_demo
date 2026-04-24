from __future__ import annotations

from skills.decorators import skill
from constraint.tool_payload_constraint import ExecuteSQLPayload
from tools.db.tool_postgres import _execute_sql_impl
from tools.db.tool_schema_store import _filter_schema_by_tables_impl, _load_database_schema_impl
from tools.llm_phases.tool_error_corrector import _correct_sql_impl
from tools.llm_phases.tool_sql_generator import _generate_sql_impl


@skill
def generate_sql_tool(plan: str, tables: list):
    """由「文本/JSON 查询计划」直接生成 PostgreSQL（str）。

    注意：主 NL2SQL Agent **未挂载**本技能，流程强制「DSL → generate_sql_from_dsl_tool」。仅保留供扩展或独立脚本导入 `skills.skill_sql` 模块时使用。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    schema = _filter_schema_by_tables_impl(all_db, tables)
    return _generate_sql_impl(plan, schema)


@skill
def generate_sql_from_dsl_tool(dsl: dict, tables: list):
    """由结构化 DSL（dict）生成 PostgreSQL（str）。

    何时调用：在 generate_dsl_tool 成功得到 dsl 之后；标准推荐路径的一环。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    schema = _filter_schema_by_tables_impl(all_db, tables)
    return _generate_sql_impl(dsl, schema)


@skill
def execute_sql_tool(sql: str) -> ExecuteSQLPayload:
    """在配置库上执行 SELECT（或允许语句），返回列/行或错误信息（ExecuteSQLPayload）。

    何时调用：已得到待验证或可交付的 SQL 后；执行失败时应结合错误信息调用 correct_sql_tool 再重试（最多约 3 次）。
    """
    return _execute_sql_impl(sql)


@skill
def correct_sql_tool(user_input: str, sql: str, error: str):
    """根据数据库报错信息修正 SQL（str）。

    何时调用：execute_sql_tool 返回 error / 语法或语义失败时；或结果明显与需求不符且错误信息可描述时。
    """
    all_db = _load_database_schema_impl(validate_on_startup=False)
    return _correct_sql_impl(user_input, sql, error, all_db)
