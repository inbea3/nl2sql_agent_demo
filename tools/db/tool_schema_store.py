from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from .tool_db_settings import DB_CONFIG
from .tool_pg_schema_introspection import _fetch_schema_payload_impl
from .tool_schema_json import _read_schema_json_impl, _write_schema_json_impl
from .tool_schema_validation import _validate_local_schema_against_db_impl

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA_PATH = os.path.abspath(
    os.getenv("NL2SQL_SCHEMA_JSON_PATH", "").strip()
    or os.path.join(_PROJECT_ROOT, "database_schema.json")
)
SCHEMA_VALIDATE_ON_STARTUP = True

_SCHEMA_VALIDATED_ONCE = False


@dataclass(frozen=True)
class SchemaCheckResult:
    ok: bool
    message: str
    local_schema: Optional[Dict[str, Any]] = None


def _refresh_local_schema_impl(schema: str = "public", out_path: str = SCHEMA_PATH) -> Dict[str, Any]:
    payload = _fetch_schema_payload_impl(DB_CONFIG, schema)
    _write_schema_json_impl(payload, out_path)
    return payload


def _validate_local_schema_impl(local_schema: Dict[str, Any]) -> None:
    _validate_local_schema_against_db_impl(
        local_schema=local_schema,
        db_config=DB_CONFIG,
        schema=str(local_schema.get("schema") or "public"),
    )


def validate_local_schema(local_schema: Dict[str, Any]) -> None:
    """对比本地 schema 与数据库签名；不一致则抛出 RuntimeError。"""
    _validate_local_schema_impl(local_schema)


def _load_database_schema_impl(validate_on_startup: bool = True) -> Dict[str, Any]:
    global _SCHEMA_VALIDATED_ONCE
    local_schema = _read_schema_json_impl(SCHEMA_PATH)

    env = os.getenv("NL2SQL_SCHEMA_VALIDATE", "").strip().lower()
    env_disable = env in {"0", "false", "no", "off"}
    should_validate = validate_on_startup and SCHEMA_VALIDATE_ON_STARTUP and not env_disable

    if should_validate and not _SCHEMA_VALIDATED_ONCE:
        auto_env = os.getenv("NL2SQL_SCHEMA_AUTO_REFRESH", "").strip().lower()
        auto_refresh = auto_env in {"1", "true", "yes", "on"}
        try:
            _validate_local_schema_impl(local_schema)
        except RuntimeError:
            if not auto_refresh:
                raise
            schema = str(local_schema.get("schema") or "public")
            local_schema = _refresh_local_schema_impl(schema=schema, out_path=SCHEMA_PATH)
            _validate_local_schema_impl(local_schema)
        _SCHEMA_VALIDATED_ONCE = True

    return local_schema


def _filter_schema_by_tables_impl(original_schema: Dict[str, Any], tables: List[str]) -> Dict[str, Any]:
    tl = [t.lower() for t in tables]
    return {
        "schema": original_schema["schema"],
        "tables": [t for t in original_schema["tables"] if t["table_name"].lower() in tl],
    }


def _check_latest_schema_once_impl(schema: str = "public") -> SchemaCheckResult:
    try:
        local = _read_schema_json_impl(SCHEMA_PATH)
    except Exception as e:
        return SchemaCheckResult(ok=False, message=f"本地 schema 文件读取失败：{e}", local_schema=None)

    try:
        _validate_local_schema_against_db_impl(
            local_schema=local,
            db_config=DB_CONFIG,
            schema=str(local.get("schema") or schema or "public"),
        )
        return SchemaCheckResult(ok=True, message="Schema 校验通过：本地与数据库一致。", local_schema=local)
    except RuntimeError as e:
        return SchemaCheckResult(ok=False, message=str(e), local_schema=local)
    except Exception as e:
        return SchemaCheckResult(ok=False, message=f"Schema 校验异常：{e}", local_schema=local)


def _refresh_local_schema_file_impl(schema: str = "public") -> SchemaCheckResult:
    try:
        local = _refresh_local_schema_impl(schema=schema, out_path=SCHEMA_PATH)
    except Exception as e:
        return SchemaCheckResult(ok=False, message=f"更新 schema 失败：{e}", local_schema=None)

    try:
        _validate_local_schema_against_db_impl(
            local_schema=local,
            db_config=DB_CONFIG,
            schema=str(local.get("schema") or schema or "public"),
        )
        return SchemaCheckResult(ok=True, message="Schema 已更新并校验通过：可继续运行。", local_schema=local)
    except Exception as e:
        return SchemaCheckResult(ok=False, message=f"Schema 已更新但校验仍失败：{e}", local_schema=local)


@tool
def load_database_schema(validate_on_startup: bool = True) -> Dict[str, Any]:
    """读取本地 schema JSON，并在进程内按需做一次启动校验。"""
    return _load_database_schema_impl(validate_on_startup=validate_on_startup)


@tool
def filter_schema_by_tables(original_schema: Dict[str, Any], tables: List[str]) -> Dict[str, Any]:
    """按表名列表过滤 schema（不区分大小写）。"""
    return _filter_schema_by_tables_impl(original_schema, tables)


@tool
def refresh_local_schema(schema: str = "public", out_path: Optional[str] = None) -> Dict[str, Any]:
    """从数据库拉取 schema 并覆盖写入本地 JSON。"""
    return _refresh_local_schema_impl(schema=schema, out_path=out_path or SCHEMA_PATH)


@tool
def check_latest_schema_once(schema: str = "public") -> SchemaCheckResult:
    """对比本地文件与数据库签名，返回结构化结果。"""
    return _check_latest_schema_once_impl(schema=schema)


@tool
def refresh_local_schema_file(schema: str = "public") -> SchemaCheckResult:
    """从数据库刷新本地 schema 文件，然后再次校验。"""
    return _refresh_local_schema_file_impl(schema=schema)
