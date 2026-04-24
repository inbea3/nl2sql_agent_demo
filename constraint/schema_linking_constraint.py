# Schema 关联阶段的结构约束
from typing import List

from pydantic import BaseModel, Field


class TableRetrievalOutput(BaseModel):
    tables: List[str] = Field(description="候选表名数组")

