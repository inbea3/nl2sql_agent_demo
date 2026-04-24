from __future__ import annotations

from skills.decorators import skill
from tools.llm_phases.tool_query_planner import _generate_query_plan_impl


@skill
def query_plan_tool(user_input: str, subproblems: str, schema: dict):
    """生成结构化查询计划（JSON 字符串，内含 CoT 步骤说明）。

    何时调用：在 subproblem_decompose_tool 之后；需要把子问题与表结构对齐成可执行计划（join/where/聚合）时。
    参数 schema：与相关表一致的过滤后 schema dict（含 tables 字段）。
    """
    return _generate_query_plan_impl(user_input, subproblems, schema)
