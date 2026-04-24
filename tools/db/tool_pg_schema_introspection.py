from __future__ import annotations

"""
PostgreSQL schema introspection（`@tool` 为对外入口；`_` 前缀为同包内部直接调用）。
"""

from typing import Any, Dict, List

import psycopg2
from langchain_core.tools import tool


def _fetch_tables_with_comments(conn, schema: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                c.relname AS table_name,
                COALESCE(obj_description(c.oid, 'pg_class'), '') AS comment
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relkind = 'r'
            ORDER BY c.relname
            """,
            (schema,),
        )
        return [{"table_name": r[0], "comment": r[1] or ""} for r in cur.fetchall()]


def _fetch_columns_with_comments(conn, schema: str, table: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.attname AS column_name,
                pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                COALESCE(col_description(a.attrelid, a.attnum), '') AS comment
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """,
            (schema, table),
        )
        return [
            {
                "column_name": r[0],
                "data_type": (r[1] or "").strip(),
                "comment": r[2] or "",
            }
            for r in cur.fetchall()
        ]


def _fetch_schema_payload_impl(db_config: Dict[str, Any], schema: str) -> Dict[str, Any]:
    conn = psycopg2.connect(**db_config)
    try:
        tables = _fetch_tables_with_comments(conn, schema)
        for t in tables:
            t["columns"] = _fetch_columns_with_comments(conn, schema, t["table_name"])
        return {"schema": schema, "tables": tables}
    finally:
        conn.close()


def _fetch_schema_signature_impl(db_config: Dict[str, Any], schema: str) -> Dict[str, Dict[str, str]]:
    conn = psycopg2.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.relname AS table_name,
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type
                FROM pg_catalog.pg_attribute a
                JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relkind = 'r'
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                ORDER BY c.relname, a.attnum
                """,
                (schema,),
            )
            sig: Dict[str, Dict[str, str]] = {}
            for table_name, column_name, data_type in cur.fetchall():
                sig.setdefault(str(table_name), {})[str(column_name)] = str(data_type)
            return sig
    finally:
        conn.close()


@tool
def fetch_schema_payload(db_config: Dict[str, Any], schema: str) -> Dict[str, Any]:
    """抓取完整 schema payload：表 + 字段 + 注释。"""
    return _fetch_schema_payload_impl(db_config, schema)


@tool
def fetch_schema_signature(db_config: Dict[str, Any], schema: str) -> Dict[str, Dict[str, str]]:
    """抓取轻量签名（table -> column -> data_type），用于一致性对比。"""
    return _fetch_schema_signature_impl(db_config, schema)
