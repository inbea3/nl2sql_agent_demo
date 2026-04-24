"""在配置的 Postgres（Neon）上执行 SQL。"""
from __future__ import annotations

import psycopg2
from langchain_core.tools import tool

from constraint.tool_payload_constraint import ExecuteSQLPayload

from .tool_db_settings import DB_CONFIG


def _execute_sql_impl(sql: str) -> ExecuteSQLPayload:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"status": "success", "columns": cols, "rows": rows}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


@tool
def execute_sql(sql: str) -> ExecuteSQLPayload:
    """在配置的 Postgres（Neon）上执行 SQL，并返回统一 payload。"""
    return _execute_sql_impl(sql)
