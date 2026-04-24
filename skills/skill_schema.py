from __future__ import annotations

from skills.decorators import skill
from tools.db.tool_schema_store import _load_database_schema_impl


@skill
def discover_schema_tool():
    """返回当前项目缓存的完整数据库 Schema（dict，默认来自仓库根目录 `database_schema.json`）。

    何时调用：处理新用户问题的起始步骤，用于确认可用表/列；若上下文已含完整 schema 且确定无变更可跳过，但默认建议先调用以避免幻觉表名。若刚执行过 `sync_local_schema_with_database_tool` 且结果为已刷新磁盘缓存，**必须**再调用本工具以加载最新结构。
    """
    return _load_database_schema_impl(validate_on_startup=False)
