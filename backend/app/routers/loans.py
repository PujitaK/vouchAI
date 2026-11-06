"""Loan origination, resolution, and listing endpoints."""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import verify_admin_key
from ..db import get_db
from ..models import Agent, Loan, utcnow
from ..schemas import LoanOut, LoanRequest, LoanResolution
from ..services import memory, underwriter
from ..services.identity import check_identity
from ..services.scoring import LoanSample, TaskSample, compute_score

router = APIRouter(tags=["loans"])

DEFAULT_BANK_ID = "vouchai-lender-main"


def _score_for(agent: Agent):
    tasks = [
        TaskSample(task.success, task.amount)
        for task in sorted(agent.task_records, key=lambda record: (record.ts, record.id))
    ]
    loans = [LoanSample(loan.status) for loan in agent.loans]
    return compute_score(tasks, loans)


def _loan_out(
    loan: Loan,
    memory_latency_ms: float | None = None,
    llm_latency_ms: float | None = None,
    total_latency_ms: float | None = None,
    identity_blocked: bool | None = None,
) -> LoanOut:
    try:
        memory_facts = json.loads(loan.memory_facts or "[]")
    except (TypeError, json.JSONDecodeError):
        memory_facts = []

    is_blocked = (
        identity_blocked
        if identity_blocked is not None
        else (loan.rationale or "").startswith("Identity gate:")
    )

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
        identity_blocked=is_blocked,
        memory_used=loan.memory_used,
        memory_facts=memory_facts,
        memory_latency_ms=memory_latency_ms,
        llm_latency_ms=llm_latency_ms,
        total_latency_ms=total_latency_ms,
        created_at=loan.created_at,
        resolved_at=loan.resolved_at,
    )


@router.get("/loans", response_model=list[LoanOut])
def list_loans(db: Session = Depends(get_db)) -> list[LoanOut]:
    loans = db.scalars(
        select(Loan)
        .options(selectinload(Loan.agent))
        .order_by(Loan.created_at.desc(), Loan.id.desc())
    ).all()
    return [_loan_out(loan) for loan in loans]


@router.post(
    "/loans/{agent_id}",
    response_model=LoanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_loan(
    agent_id: int,
    payload: LoanRequest,
    db: Session = Depends(get_db),
) -> LoanOut:
    agent = db.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .options(
            selectinload(Agent.principal),
            selectinload(Agent.task_records),
            selectinload(Agent.loans),
        )
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    started = time.perf_counter()

    gate_result = check_identity(db, agent)
    if not gate_result.passed:
        rationale = f"Identity gate: {'; '.join(gate_result.reasons)}"
        loan = Loan(
            agent_id=agent.id,
            requested_amount=payload.amount,
            formula_limit=0.0,
            final_limit=0.0,
            multiplier=0.0,
            decision="denied",
            rationale=rationale,
            status="denied",
            memory_used=False,
            memory_facts="[]",
        )
        db.add(loan)
        db.commit()
        db.refresh(loan)

        total_latency_ms = (time.perf_counter() - started) * 1000.0
        return _loan_out(
            loan,
            memory_latency_ms=0.0,
            llm_latency_ms=0.0,
            total_latency_ms=round(total_latency_ms, 1),
            identity_blocked=True,
        )

    breakdown = _score_for(agent)

    memory_facts: list[str] = []
    memory_latency_ms: float | None = None
    if payload.use_memory:
        memory.ensure_bank(payload.bank_id)
        memory_facts, memory_latency_ms = memory.recall_context(
            payload.bank_id,
            agent.name,
            agent.principal.name,
            agent.category,
        )

    outcome = underwriter.decide(
        agent=agent.name,
        principal=agent.principal.name,
        category=agent.category,
        amount=payload.amount,
        formula=breakdown,
        memory_facts=memory_facts,
        memory_on=payload.use_memory,
    )

    loan = Loan(
        agent_id=agent.id,
        requested_amount=payload.amount,
        formula_limit=breakdown.formula_limit,
        final_limit=outcome["final_limit"],
        multiplier=outcome["multiplier"],
        decision=outcome["decision"],
        rationale=outcome["rationale"],
        status="active" if outcome["decision"] == "approved" else "denied",
        memory_used=payload.use_memory,
        memory_facts=json.dumps(outcome["memory_facts"]),
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    if payload.use_memory:
        memory.retain_decision(
            payload.bank_id,
            agent.name,
            agent.principal.name,
            agent.category,
            payload.amount,
            outcome["decision"],
            outcome["rationale"],
        )

    total_latency_ms = (time.perf_counter() - started) * 1000.0
    return _loan_out(
        loan,
        memory_latency_ms=memory_latency_ms,
        llm_latency_ms=outcome.get("llm_latency_ms"),
        total_latency_ms=round(total_latency_ms, 1),
    )


@router.post(
    "/loans/{loan_id}/resolve",
    response_model=LoanOut,
    dependencies=[Depends(verify_admin_key)],
)
def resolve_loan(
    loan_id: int,
    payload: LoanResolution,
    db: Session = Depends(get_db),
) -> LoanOut:
    loan = db.scalar(
        select(Loan)
        .where(Loan.id == loan_id)
        .options(selectinload(Loan.agent).selectinload(Agent.principal))
    )
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")
    if loan.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Only active loans can be resolved",
        )

    loan.status = payload.outcome
    loan.resolved_at = utcnow()
    db.commit()
    db.refresh(loan)

    if loan.memory_used:
        memory.ensure_bank(payload.bank_id)
        memory.retain_outcome(
            payload.bank_id,
            loan.agent.name,
            loan.agent.principal.name,
            loan.agent.category,
            loan.requested_amount,
            payload.outcome,
        )

    return _loan_out(loan)
