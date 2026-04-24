langchain-project/
├── README.md
├── .env
├── .gitignore
├── requirements.txt
│
├── app/                    # 应用层（入口与编排），不思考业务，只拉线
│   ├── gradio_app.py       # Web 启动入口
│   ├── ...
│
├── prompts/                # Prompts，单独抽离
│   ├── __init__.py
│   ├── 1_prompt.py
│
├── models/                 # 模型隔离层，可以实现模型切换等
│   ├── __init__.py
│   ├── ...
│
（已合并）schema 加载/校验/刷新能力在 `tools/db/tool_schema_store.py`（及 `tool_schema_validation.py`、`tool_pg_schema_introspection.py`、`tool_schema_json.py`）
│   ├── __init__.py
│   ├── ...
│
├── skills/                 # Agent 可调用的 @skill 技能（skill_*.py；调用 tools/ 实现）
│   ├── __init__.py
│   ├── ...
│
├── tools/                  # 实现层：`db/tool_*.py`、`llm_phases/tool_*.py`（@tool + _impl）
│   ├── __init__.py
│   ├── db/
│   ├── llm_phases/
│   ├── ...
│
├── memory/                 # 记忆机制，对话的时间维度
│   ├── __init__.py
│   ├── ...
│
├── services/               # 专属领域服务,非LangChain逻辑，放业务规则，放数据库逻辑，放非 AI 判断
│   ├── __init__.py
│   ├── ...
│
（已删除）`api/`：对外接口层占位目录，目前项目使用 Gradio 作为前端入口，暂不提供 HTTP API。
│   ├── __init__.py
│   ├── router.py
│   └── schemas.py
│
├── scripts/                # 一次性脚本
│   ├── ...
|
├── else/                   # 其他内容（流程图、多余md文件）
│   ├── ...
