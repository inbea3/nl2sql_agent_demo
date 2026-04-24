## 项目架构（目录结构）

每个子目录都包含 `README.md` 用于说明职责与约定。

```text
nl2sql_langchain_demo_421/
├── README.md
├── requirements.txt
├── database_schema.json    # 本地缓存的数据库 schema（与代码并列，便于编辑/对比）
├── .env / .env.example
│
├── app/                    # 入口与编排（Gradio）
│   ├── gradio_app.py        # Web 启动入口：python -m app.gradio_app
│   ├── gradio_ui.py         # Gradio 展示层与回调（schema 校验/更新；触发后端 Agent）
│   └── nl2sql_agent.py      # LangGraph ReAct Agent（挂载 skills；system prompt 约束阶段）
│
├── skills/                 # Agent 可调用的技能（`skill_*.py`，`@skill` 入口；内部调用 tools/db、tools/llm_phases）
├── tools/                  # 实现层：`db/tool_*.py`、`llm_phases/tool_*.py`（`@tool` + `_impl`）
├── prompts/                # 提示词模板（system/user prompt 片段与兜底提示）
├── constraint/             # 结构化输出约束（Pydantic 数据契约）
├── models/                 # LLM 构造与配置（从环境变量读取，便于替换）
├── memory/                 # LangGraph checkpointer（MemorySaver）
│
├── domain/                 # 领域规则/指标口径（确定性知识）
└── appendix/               # 附录资料（流程图、说明等，不参与运行）
```

整体上这是一个“7 阶段”的 NL2SQL 能力：**阶段逻辑在 `tools/llm_phases/tool_*.py` 实现（`@tool`），经 `skills/skill_*.py` 中的 `@skill` 技能暴露给 LangGraph ReAct Agent**；由模型按 system prompt 与技能说明决定调用时机，完成 **表/字段发现与关联 → 拆解与规划 → DSL/SQL 生成 → 执行 → 出错纠正与重试**，最后将 SQL 与执行结果返回给前端展示。
其中：
- **Web（Gradio）**：仅负责输入解析、Schema 校验与结果展示；`app/gradio_ui.py::run_nl2sql()` 调用 `NL2SQL7PhaseAgent.run_for_gradio()`，**不在前端重复编排确定性流水线**。

## 快速开始（Web）

```bash
pip install -r requirements.txt
python -m app.gradio_app
```

浏览器打开 `http://127.0.0.1:7860`。

## 配置（.env）

从 `.env.example` 复制生成 `.env`，至少填写：
- **LLM**：`NL2SQL_API_KEY`（可选：`NL2SQL_BASE_URL`、`NL2SQL_MODEL_NAME`）
- **DB/Neon**：`NL2SQL_DB_HOST`、`NL2SQL_DB_DATABASE`、`NL2SQL_DB_USER`、`NL2SQL_DB_PASSWORD`（可选：`NL2SQL_DB_PORT`、`NL2SQL_DB_SSLMODE`）

## Schema（本地缓存 + 启动校验/更新）

- **本地缓存文件**：项目根目录 `database_schema.json`（可用环境变量 `NL2SQL_SCHEMA_JSON_PATH` 指定其它绝对路径）
- **前端启动时行为**：页面加载会自动做一次“远端签名对比”  
  - 一致：可直接运行  
  - 不一致：界面提示差异，并提供按钮一键更新本地 schema

## 目录结构（核心）

- `app/`：入口与编排（Gradio）
- `skills/`：Agent 挂载的 `@skill` 技能（`skill_*.py`；编排对 `tools/` 的调用）
- `tools/`：`db/tool_*.py`（连库、schema 文件、SQL 执行，`@tool`）+ `llm_phases/tool_*.py`（各阶段 LLM，`@tool`）
- `domain/`：领域规则/指标口径（确定性知识）
- `prompts/`：提示词模板
- `constraint/`：结构化输出约束（Pydantic）
- `memory/`：LangGraph checkpointer