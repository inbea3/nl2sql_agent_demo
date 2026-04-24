from __future__ import annotations

import json
import os
from typing import Any, Dict

from langchain_core.tools import tool


def _read_schema_json_impl(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_schema_json_impl(payload: Dict[str, Any], path: str) -> str:
    out_path = os.path.abspath(path)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


@tool
def read_schema_json(path: str) -> Dict[str, Any]:
    """读取 schema JSON 文件。"""
    return _read_schema_json_impl(path)


@tool
def write_schema_json(payload: Dict[str, Any], path: str) -> str:
    """写入 schema JSON 文件，返回写入的绝对路径。"""
    return _write_schema_json_impl(payload, path)
