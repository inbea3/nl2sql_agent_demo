# `tools/db/` 说明

原 `data_access/` 目录下的数据库连接、SQL 执行、schema 拉取/校验/本地 JSON 缓存已全部迁入此处，供 **`skills/`**（`@skill` 编排）与 **`app/`** 引用。

## 本地 schema 与常量

- 默认使用**项目根目录** `database_schema.json` 作为本地缓存（常量 **`tools.db.tool_schema_store.SCHEMA_PATH`**；可用环境变量 `NL2SQL_SCHEMA_JSON_PATH` 覆盖为绝对路径）。

## 模块一览（文件名均以 `tool_` 开头；对外能力用 LangChain **`@tool`**）

| 文件 | 职责 |
|------|------|
| `tool_db_settings.py` | 连接配置（环境变量 → `DB_CONFIG`） |
| `tool_postgres.py` | `execute_sql`（Neon/Postgres 执行） |
| `tool_pg_schema_introspection.py` | 从系统表拉取结构签名与 payload |
| `tool_schema_json.py` | `read_schema_json` / `write_schema_json` |
| `tool_schema_validation.py` | `validate_local_schema_against_db`（本地与远端签名对比） |
| `tool_schema_store.py` | `load_database_schema`、`filter_schema_by_tables`、刷新/启动校验等；另有 **`validate_local_schema`** 供非 Agent 代码直接调用 |

## 包入口

```python
from tools.db import load_database_schema, execute_sql, SCHEMA_PATH
# 或按需：
from tools.db.tool_schema_store import _load_database_schema_impl, SCHEMA_PATH
```
