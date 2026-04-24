# 阶段3：子问题分解提示词（提示词统一维护在 prompts/）

SUBPROBLEM_DECOMPOSER_PROMPT_TEMPLATE = (
    "用户问题：{user_input}\n"
    "结构：{schema}\n"
    "拆解为可执行子问题。"
)

