"""Loan origination, resolution, and listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Agent, Loan
from ..models import utcnow
from ..schemas import LoanOut, LoanRequest, LoanResolution
from ..services.scoring import LoanSample, TaskSample, compute_score

router = APIRouter(tags=["loans"])


def _score_for(agent: Agent):
    tasks = [
        TaskSample(task.success, task.amount)
        for task in sorted(agent.task_records, key=lambda record: (record.ts, record.id))
    ]
    loans = [LoanSample(loan.status) for loan in agent.loans]
    return compute_score(tasks, loans)


def _loan_out(loan: Loan) -> LoanOut:
    return LoanOut(
        id=loan.id,
        agent_id=loan.agent_id,
        agent_name=loan.agent.name if loan.agent else None,
        requested_amount=loan.requested_amount,
        formula_limit=loan.formula_limit,
        final_limit=loan.final_limit,
        decision=loan.decision,
        rationale=loan.rationale,
        status=loan.status,
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
        .options(selectinload(Agent.task_records), selectinload(Agent.loans))
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    breakdown = _score_for(agent)
    approved = payload.amount <= breakdown.formula_limit
    decision = "approved" if approved else "denied"
    final_limit = breakdown.formula_limit if approved else 0.0

    if approved:
        rationale = (
            f"Approved {payload.amount:.2f} for {payload.purpose}: within formula "
            f"limit {breakdown.formula_limit} (score {breakdown.score:.1f}, "
            f"confidence {breakdown.confidence:.2f})."
        )
    else:
        rationale = (
            f"Denied {payload.amount:.2f} for {payload.purpose}: exceeds formula "
            f"limit {breakdown.formula_limit} (score {breakdown.score:.1f}, "
            f"confidence {breakdown.confidence:.2f})."
        )

    loan = Loan(
        agent_id=agent.id,
        requested_amount=payload.amount,
        formula_limit=breakdown.formula_limit,
        final_limit=final_limit,
        decision=decision,
        rationale=rationale,
        status="active" if approved else "denied",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return _loan_out(loan)


@router.post("/loans/{loan_id}/resolve", response_model=LoanOut)
def resolve_loan(
    loan_id: int,
    payload: LoanResolution,
    db: Session = Depends(get_db),
) -> LoanOut:
    loan = db.scalar(
        select(Loan).where(Loan.id == loan_id).options(selectinload(Loan.agent))
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
    return _loan_out(loan)
