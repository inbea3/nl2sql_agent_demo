# Schema 关联提示词（提示词统一维护在 prompts/）

SCHEMA_LINKING_SYSTEM_PROMPT_TEMPLATE = (
    "数据库结构：{schema}\n"
    "只返回相关表名数组。\n\n"
    "{format_instructions}"
)

