# `prompts/` 目录说明

存放 **所有注入大模型的提示词/模板**（system/user prompt 片段、重试/兜底提示、任务包装模板等）。
目标是：**代码只负责组装与传参，提示词文本统一在这里维护**，便于版本化与迭代。

### 文件清单（按用途）

- **7阶段总控（System Prompt）**
  - **`workflow_system_prompt.py`**：7阶段工作流的 system prompt 模板与 `get_7phase_system_prompt()`。

- **阶段2：Schema 关联**
  - **`schema_linker_prompt.py`**：Schema 关联的 system prompt 模板（配合 `PydanticOutputParser`）。

- **阶段4：查询计划（查询规划）**
  - **`query_planner_prompt.py`**：查询计划生成 prompt 模板。

- **阶段3：子问题分解**
  - **`subproblem_decomposer_prompt.py`**：子问题分解 prompt 模板。

- **阶段5.1：DSL 生成**
  - **`dsl_generator_prompt.py`**：DSL 生成 system/user prompt 模板，以及“硬约束候选提示”的片段常量。

- **阶段5.2：SQL 生成**
  - **`sql_generator_prompt.py`**：从计划/DSL + schema 生成 PostgreSQL 的 prompt 模板。

- **阶段7：错误纠正**
  - **`error_corrector_prompt.py`**：SQL 纠错 prompt 模板（只输出可执行 SQL）。

- **外层输入包装**
  - **`user_query_prompt.py`**：把“业务需求 + 统计维度”包装为发给 Agent 的统一任务描述（`build_user_query()`）。

业务指标口径文本在 **`domain/risk_metrics.py`**（`METRIC_DICTION_PROMPT`），由 DSL 生成与 workflow system prompt 引用。

### 维护约定

- **只放“文本与模板”**：prompt 的正文、模板、片段常量都放 `prompts/`；业务逻辑与链路编排留在 `app/`、`skills/`、`tools/`。
- **模板优先用 `.format()`**：保持变量名清晰一致（例如 `schema`、`user_input`、`subproblems`、`original_sql`）。
- **新增 prompt 的步骤**
  - 在 `prompts/` 新建 `*_prompt.py`（或按模块命名）并暴露常量/函数
  - 在调用侧（例如 `tools/llm_phases/tool_*.py`）只引用模板并传参，不再内联长字符串
