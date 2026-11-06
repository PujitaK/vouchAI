"""Agent listing and detail endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Agent, Loan
from ..schemas import AgentDetail, AgentSummary, LoanOut, TaskRecordOut
from ..services.scoring import LoanSample, TaskSample, compute_score

router = APIRouter(tags=["agents"])


def _ordered_tasks(agent: Agent) -> list:
    return sorted(agent.task_records, key=lambda record: (record.ts, record.id))


def _score_for(agent: Agent):
    tasks = [TaskSample(task.success, task.amount) for task in _ordered_tasks(agent)]
    loans = [LoanSample(loan.status) for loan in agent.loans]
    return compute_score(tasks, loans)


def _loan_out(loan: Loan) -> LoanOut:
    try:
        memory_facts = json.loads(loan.memory_facts or "[]")
    except (TypeError, json.JSONDecodeError):
        memory_facts = []

    return LoanOut(
        id=loan.id,
        agent_id=loan.agent_id,
        agent_name=loan.agent.name if loan.agent else None,
        requested_amount=loan.requested_amount,
        formula_limit=loan.formula_limit,
        final_limit=loan.final_limit,
        multiplier=loan.multiplier,
        decision=loan.decision,
        rationale=loan.rationale,
        status=loan.status,
        identity_blocked=(loan.rationale or "").startswith("Identity gate:"),
        memory_used=loan.memory_used,
        memory_facts=memory_facts,
        created_at=loan.created_at,
        resolved_at=loan.resolved_at,
    )


@router.get("/agents", response_model=list[AgentSummary])
def list_agents(db: Session = Depends(get_db)) -> list[AgentSummary]:
    agents = db.scalars(
        select(Agent)
        .options(
            selectinload(Agent.principal),
            selectinload(Agent.task_records),
            selectinload(Agent.loans),
        )
        .order_by(Agent.id)
    ).all()

    summaries: list[AgentSummary] = []
    for agent in agents:
        breakdown = _score_for(agent)
        summaries.append(
            AgentSummary(
                id=agent.id,
                name=agent.name,
                principal=agent.principal.name,
                category=agent.category,
                score=breakdown.score,
                confidence=breakdown.confidence,
                formula_limit=breakdown.formula_limit,
            )
        )
    return summaries


@router.get("/agents/{agent_id}", response_model=AgentDetail)
def get_agent(agent_id: int, db: Session = Depends(get_db)) -> AgentDetail:
    agent = db.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.principal),
            selectinload(Agent.task_records),
            selectinload(Agent.loans).selectinload(Loan.agent),
        )
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    breakdown = _score_for(agent)
    recent = list(reversed(_ordered_tasks(agent)[-20:]))
    loans = sorted(agent.loans, key=lambda loan: (loan.created_at, loan.id), reverse=True)

    return AgentDetail(
        id=agent.id,
        name=agent.name,
        principal=agent.principal.name,
        category=agent.category,
        created_at=agent.created_at,
        score=breakdown.score,
        confidence=breakdown.confidence,
        formula_limit=breakdown.formula_limit,
        components=breakdown.components,
        recent_tasks=[TaskRecordOut.model_validate(record) for record in recent],
        loans=[_loan_out(loan) for loan in loans],
    )
