# 阶段7：错误纠正提示词（提示词统一维护在 prompts/）

ERROR_CORRECTOR_PROMPT_TEMPLATE = """你是 PostgreSQL 专家，请修正 SQL，使其可在当前数据库上成功执行并满足需求。

【需求】
{user_input}

【执行错误】
{error_msg}

【原 SQL】
{original_sql}

【数据库结构】
{schema}

【输出要求（非常重要）】
1) 只输出一段可执行的 PostgreSQL SQL
2) 不要输出任何解释文字、步骤、Markdown 代码块
3) 如果需要改表名/字段名/连接键，必须来自给定 schema
"""

