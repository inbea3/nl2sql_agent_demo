# 阶段5.2：SQL 生成提示词（提示词统一维护在 prompts/）

SQL_GENERATION_PROMPT_TEMPLATE = """生成PostgreSQL：
输入类型：{input_type}
输入：{plan}
结构：{schema}
要求：
1) 仅输出可执行 SQL（不要 Markdown 代码块，不要解释）
2) 若需要 JOIN，请基于 schema 中字段合理推断连接键，并显式写出 JOIN 条件
3) 避免 SELECT *；只选择必要字段
"""

