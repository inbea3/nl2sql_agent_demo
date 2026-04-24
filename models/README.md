# `models/` 目录说明

`models/` 是模型封装层：负责构造与配置 LLM（从环境变量读取参数，便于替换不同模型/平台）。

- `env.py`：环境变量加载（`.env`）
- `llm_settings.py`：LLM 配置读取
- `llm.py`：Chat 模型构造入口

