# `constraint/` 目录说明

使用 **Pydantic 模型** 定义 LLM 结构化输出与中间表示的约束（数据契约），供 LangChain 解析器或业务代码校验。

- **`schema_linking_constraint.py`**：Schema 关联阶段输出约束（如 `TableRetrievalOutput`）。
- **`dsl_constraint.py`**：DSL/中间表示输出约束（如 `DSLOutput` 及其子结构）。
- **`tool_payload_constraint.py`**：工具返回 payload 的结构约束（如 `ExecuteSQLPayload`）。

与 `tools/llm_phases/tool_schema_linker.py`、`tools/llm_phases/tool_dsl_generator.py` 等配合，减少非 JSON/非结构化回复带来的解析失败。

