# `skills/` 目录说明

本目录存放 **供 LangGraph Agent 选择的技能**：每个对外能力是一个用 **`@skill`** 装饰的函数（`skills.decorators` 将 LangChain 的 `tool` 别名化为 `skill`，在框架里仍注册为可调用的 *tool*）。

## 文件命名

- 技能模块文件名以 **`skill_`** 开头，例如 `skill_schema.py`、`skill_sql.py`。

## 与 `tools/` 的分工

| 层级 | 包路径 | 职责 |
|------|--------|------|
| **技能** | `skills/skill_*.py` | `@skill` 入口；描述「何时调用」；内部编排对下层 `_*_impl` 或 `tools` 上 `@tool` 的调用 |
| **工具（实现）** | `tools/db/tool_*.py`、`tools/llm_phases/tool_*.py` | 连库、读写 schema 文件、各阶段 LLM 链与解析；对外能力使用 LangChain **`@tool`** |

约定：**Agent 只挂载 `skills/` 下的函数**；`tools/` 中的实现以 `tool_*.py` 为模块边界，供技能与 `app/` 按需引用（业务热路径可优先调用各模块内的 `_…_impl`，避免重复包一层 tool）。
