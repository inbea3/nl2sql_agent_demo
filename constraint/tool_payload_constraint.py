# 工具返回 payload 的结构约束（数据契约）
from __future__ import annotations

from typing import Any, Literal, Sequence, TypedDict, Union


class ExecuteSQLSuccessPayload(TypedDict):
    status: Literal["success"]
    columns: list[str]
    rows: list[Sequence[Any]]


class ExecuteSQLErrorPayload(TypedDict):
    status: Literal["error"]
    msg: str


ExecuteSQLPayload = Union[ExecuteSQLSuccessPayload, ExecuteSQLErrorPayload]

