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
    multiplier: float = 1.0
    decision: str
    rationale: str
    status: str
    identity_blocked: bool = False
    memory_used: bool = False
    memory_facts: list[str] = Field(default_factory=list)
    memory_latency_ms: float | None = None
    llm_latency_ms: float | None = None
    total_latency_ms: float | None = None
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
    use_memory: bool = True
    bank_id: str = "vouchai-lender-main"


class LoanResolution(BaseModel):
    outcome: Literal["repaid", "defaulted"]
    bank_id: str = "vouchai-lender-main"


class MemoryRecallOut(BaseModel):
    agent_id: int
    bank_id: str
    facts: list[str]
    latency_ms: float


class MemoryBeliefsOut(BaseModel):
    bank_id: str
    beliefs: str
    latency_ms: float
