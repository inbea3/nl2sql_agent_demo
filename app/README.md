# `app/` 目录说明

`app/` 是**应用层/编排层**，负责把各模块“拉线”组合起来，对外提供可运行入口。

- `gradio_app.py`：Web 启动入口（启动 Gradio）
- `gradio_ui.py`：Gradio 展示与回调（启动时 schema 校验/更新；运行按钮仅转调 Agent）
- `nl2sql_agent.py`：LangGraph ReAct Agent（挂载 `skills/skill_*.py` 各阶段 `@skill`；`run_for_gradio` 供界面取 DSL/SQL/执行结果）


