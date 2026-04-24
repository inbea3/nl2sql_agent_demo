from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from .tool_pg_schema_introspection import _fetch_schema_signature_impl


def local_signature(local_schema: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    sig: Dict[str, Dict[str, str]] = {}
    for t in local_schema.get("tables", []) or []:
        tname = str(t.get("table_name", ""))
        cols: Dict[str, str] = {}
        for c in t.get("columns", []) or []:
            cname = str(c.get("column_name", ""))
            ctype = str(c.get("data_type", ""))
            if cname:
                cols[cname] = ctype
        if tname:
            sig[tname] = cols
    return sig


def diff_signatures(
    local_sig: Dict[str, Dict[str, str]],
    remote_sig: Dict[str, Dict[str, str]],
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []

    local_tables = set(local_sig.keys())
    remote_tables = set(remote_sig.keys())
    missing_tables = sorted(remote_tables - local_tables)
    extra_tables = sorted(local_tables - remote_tables)

    if missing_tables:
        errors.append(f"缺少表（本地无/数据库有）：{missing_tables}")
    if extra_tables:
        errors.append(f"多出表（本地有/数据库无）：{extra_tables}")

    common = sorted(local_tables & remote_tables)
    for t in common:
        lcols = local_sig.get(t, {})
        rcols = remote_sig.get(t, {})
        lset = set(lcols.keys())
        rset = set(rcols.keys())
        miss_cols = sorted(rset - lset)
        extra_cols = sorted(lset - rset)
        if miss_cols:
            errors.append(f"表 {t} 缺少字段（本地无/数据库有）：{miss_cols}")
        if extra_cols:
            errors.append(f"表 {t} 多出字段（本地有/数据库无）：{extra_cols}")
        for c in sorted(lset & rset):
            if str(lcols.get(c, "")).strip() != str(rcols.get(c, "")).strip():
                errors.append(
                    f"表 {t} 字段类型不一致：{c} 本地={lcols.get(c)!r} 数据库={rcols.get(c)!r}"
                )

    summary: List[str] = []
    if errors:
        summary.append(
            f"本地 schema 与数据库 schema 不一致（tables={len(local_tables)} vs {len(remote_tables)}）。"
        )
    return errors, summary


def _validate_local_schema_against_db_impl(
    *,
    local_schema: Dict[str, Any],
    db_config: Dict[str, Any],
    schema: Optional[str] = None,
    fetch_script_hint: str = 'python -c "from tools.db.tool_schema_store import refresh_local_schema_file; refresh_local_schema_file.invoke({\\"schema\\": \\"public\\"})"',
) -> None:
    resolved_schema = str(schema or local_schema.get("schema") or "public")
    local_sig = local_signature(local_schema)
    remote_sig = _fetch_schema_signature_impl(db_config, resolved_schema)
    errors, summary = diff_signatures(local_sig, remote_sig)
    if not errors:
        return

    head = 80
    shown = errors[:head]
    more = len(errors) - len(shown)

    lines: List[str] = []
    lines.extend(summary)
    lines.append(f"- 校验 schema：{resolved_schema!r}")
    lines.append("- 说明：本检查仅对比表/字段/类型，不对比注释。")
    lines.append("- 不一致明细：")
    lines.extend([f"  - {e}" for e in shown])
    if more > 0:
        lines.append(f"  - ... 还有 {more} 条差异未展示")
    lines.append("")
    lines.append("请更新本地 schema 文件后重试：")
    lines.append(f"  {fetch_script_hint}")

    raise RuntimeError("\n".join(lines))


@tool
def validate_local_schema_against_db(
    local_schema: Dict[str, Any],
    db_config: Dict[str, Any],
    schema: Optional[str] = None,
) -> str:
    """对比本地 schema 与数据库签名；不一致则抛错（此处返回 ok 字符串表示通过）。"""
    _validate_local_schema_against_db_impl(
        local_schema=local_schema, db_config=db_config, schema=schema
    )
    return "ok"
