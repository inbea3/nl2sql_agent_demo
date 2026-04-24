from __future__ import annotations

from typing import Any

from skills.decorators import skill
from tools.db.tool_schema_store import (
    _check_latest_schema_once_impl,
    _refresh_local_schema_file_impl,
)


@skill
def sync_local_schema_with_database_tool(force_refresh: bool = False) -> dict[str, Any]:
    """对比本地 schema 缓存文件（默认仓库根目录 `database_schema.json`）与数据库当前结构签名；不一致则从库拉取并覆盖本地文件。

    何时调用（自行判断其一即可）：
    - 用户明确说表结构/字段/库有变更、要「同步 schema」「更新缓存」等；
    - `execute_sql_tool` 报错提示缺表、缺列、对象不存在，且怀疑本地缓存陈旧；
    - 在开始复杂 NL2SQL 前希望确认本地与线上一致（可先本技能再 `discover_schema_tool`）。

    行为：
    - `force_refresh=False`（默认）：先校验；已一致则**不**写盘，返回 `action=already_in_sync`；不一致则拉库覆盖本地 JSON，返回 `action=refreshed`。
    - `force_refresh=True`：**跳过**对比，直接从数据库拉取并覆盖本地文件（慎用，仅当用户要求强制刷新时）。

    刷新成功后：应再次调用 `discover_schema_tool()`，再继续阶段 2 及以后（保证后续技能读到最新结构）。
    """
    if not force_refresh:
        check = _check_latest_schema_once_impl()
        if check.ok:
            return {
                "ok": True,
                "action": "already_in_sync",
                "message": check.message,
            }
    refresh = _refresh_local_schema_file_impl()
    return {
        "ok": refresh.ok,
        "action": "refreshed" if refresh.ok else "refresh_failed",
        "message": refresh.message,
    }
