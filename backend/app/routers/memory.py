"""Read-only memory inspection endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import public_demo_enabled
from ..cost_guard import enforce_cost_guard
from ..db import get_db
from ..models import Agent
from ..schemas import MemoryBeliefsOut, MemoryRecallOut
from ..services import memory

router = APIRouter(prefix="/memory", tags=["memory"])

DEFAULT_BANK_ID = "vouchai-lender-main"
BELIEF_QUESTION = (
    "What patterns have you learned about which agents, fleets and task "
    "categories default?"
)


@router.get(
    "/recall",
    response_model=MemoryRecallOut,
    dependencies=[Depends(enforce_cost_guard)],
)
def recall_memory(
    agent_id: int,
    bank_id: str = DEFAULT_BANK_ID,
    db: Session = Depends(get_db),
) -> MemoryRecallOut:
    agent = db.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(selectinload(Agent.principal))
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not public_demo_enabled():
        memory.ensure_bank(bank_id)
    facts, latency_ms = memory.recall_context(
        bank_id,
        agent.name,
        agent.principal.name,
        agent.category,
    )
    return MemoryRecallOut(
        agent_id=agent.id,
        bank_id=bank_id,
        facts=facts,
        latency_ms=round(latency_ms, 1),
    )


@router.get(
    "/beliefs",
    response_model=MemoryBeliefsOut,
    dependencies=[Depends(enforce_cost_guard)],
)
def memory_beliefs(
    bank_id: str = DEFAULT_BANK_ID,
) -> MemoryBeliefsOut:
    started = time.perf_counter()
    if not public_demo_enabled():
        memory.ensure_bank(bank_id)
    beliefs = memory.reflect_beliefs(bank_id, BELIEF_QUESTION)
    latency_ms = (time.perf_counter() - started) * 1000.0
    return MemoryBeliefsOut(
        bank_id=bank_id,
        beliefs=beliefs,
        latency_ms=round(latency_ms, 1),
    )
