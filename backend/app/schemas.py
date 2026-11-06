"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthOut(BaseModel):
    status: str


class AgentSummary(BaseModel):
    id: int
    name: str
    principal: str
    category: str
    score: float
    confidence: float
    formula_limit: int


class TaskRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    success: bool
    amount: float
    ts: datetime


class LoanOut(BaseModel):
    id: int
    agent_id: int
    agent_name: str | None = None
    requested_amount: float
    formula_limit: float
    final_limit: float
    decision: str
    rationale: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AgentDetail(BaseModel):
    id: int
    name: str
    principal: str
    category: str
    created_at: datetime
    score: float
    confidence: float
    formula_limit: int
    components: dict[str, float]
    recent_tasks: list[TaskRecordOut]
    loans: list[LoanOut]


class LoanRequest(BaseModel):
    amount: float = Field(gt=0)
    purpose: str = Field(min_length=1, max_length=500)


class LoanResolution(BaseModel):
    outcome: Literal["repaid", "defaulted"]
