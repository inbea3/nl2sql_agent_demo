# DSL / SQL 中间表示的结构约束
from typing import List, Optional

from pydantic import BaseModel


class FieldItem(BaseModel):
    table: str
    field: str


class AggregationItem(BaseModel):
    table: str
    field: str
    func: str


class CaseExpressionItem(BaseModel):
    table: str
    field: str
    expr: str


class MetricItem(BaseModel):
    table: str
    field: str
    expr: str


class WhereConditionItem(BaseModel):
    type: str
    field: str
    value: str


class DSLOutput(BaseModel):
    select_fields: List[FieldItem] = []
    aggregations: List[AggregationItem] = []
    case_expressions: List[CaseExpressionItem] = []
    metrics: List[MetricItem] = []
    from_tables: List[str] = []
    join_relations: List[str] = []
    where_conditions: List[WhereConditionItem] = []
    group_by: List[str] = []
    order_by: List[str] = []
    limit: Optional[int] = None

