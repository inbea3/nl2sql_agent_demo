# Agent 用户输入包装（提示词统一维护在 prompts/）

NL2SQL_USER_QUERY_TEMPLATE = """
请完成以下银行风控指标计算：
【业务需求】：{biz_need}
【统计维度】：{stat_dim}
请生成标准可执行的 PostgreSQL SQL，并给出结果。
""".strip()


def build_user_query(biz_need: str, stat_dim: str) -> str:
    biz_need = (biz_need or "").strip()
    stat_dim = (stat_dim or "").strip()
    if not biz_need:
        raise ValueError("业务需求不能为空")

    stat_dim_final = stat_dim if stat_dim else "无，按整体统计"
    return NL2SQL_USER_QUERY_TEMPLATE.format(biz_need=biz_need, stat_dim=stat_dim_final)

