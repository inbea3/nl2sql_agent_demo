# `tools/` 目录说明

本目录存放 **实现层工具**：模块名为 `tool_*.py`，对外能力使用 LangChain **`@tool`** 注册；由 `skills/`（`@skill` 编排）与 `app/` 按需调用。**Agent 工具列表只挂载 `skills/` 下的 `@skill`，不直接挂载本目录的 `@tool`。**

## 结构

- **`db/tool_*.py`**：数据库连接、SQL 执行、schema 拉取/校验、项目根目录 `database_schema.json` 读写等。
- **`llm_phases/tool_*.py`**：各 NL2SQL 阶段的 LLM 调用与解析（`prompts/` + 链式 `invoke`）；每个文件通常提供 `_…_impl` 与同名 `@tool`。

## 与 `skills/` 的关系

| 概念 | 位置 | 说明 |
|------|------|------|
| **技能（Skill）** | `skills/skill_*.py` | 使用 **`@skill`** 注册，由 **Agent 选择调用** |
| **工具（Tool）** | `tools/db/`、`tools/llm_phases/` | **`@tool`**；由技能组合调用，或供 `app/` 直接 `invoke` / 调 `_impl` |

## 依赖约定

- **允许**：`skills/`、`app/` 依赖 `tools/`；`tools/llm_phases/` 依赖 `constraint`、`models`、`prompts`、`domain`；`tools/db/` 依赖 `models`、`constraint`。
- **禁止**：`tools/` 依赖 `app/`、`skills/`（避免循环）。

编排顺序仍由 **LangGraph Agent + `workflow_system_prompt`** 与 **技能 docstring** 约束。
