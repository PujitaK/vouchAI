"""Identity security gating service for autonomous loan applicants."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Agent, Loan, TaskRecord


@dataclass
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def normalize_name(name: str) -> str:
    """Normalize agent name to lowercase letters and digits only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def check_identity(db: Session, agent: Agent) -> GateResult:
    """Evaluate identity security rules before loan underwriting.

    Rule 1 (Lookalike / Impersonation):
        Block if the normalized name matches another agent under a different principal.

    Rule 2 (Name Washing):
        If an agent has fewer than 5 own records (tasks + resolved loans) AND
        its principal already has 2 or more defaults across all its agents, block it.
    """
    reasons: list[str] = []
    norm_agent_name = normalize_name(agent.name)

    # Rule 1: Check other agents under different principals
    other_agents = db.scalars(
        select(Agent).where(Agent.id != agent.id)
    ).all()

    for other in other_agents:
        if other.principal_id != agent.principal_id:
            if normalize_name(other.name) == norm_agent_name:
                reasons.append(
                    f"Lookalike identity conflict: normalized name '{norm_agent_name}' "
                    f"matches agent '{other.name}' under principal '{other.principal.name}'"
                )
                break

    # Rule 2: Name washing check
    # Own records = task records + resolved loans (repaid or defaulted)
    task_count = db.scalar(
        select(func.count(TaskRecord.id)).where(TaskRecord.agent_id == agent.id)
    ) or 0

    resolved_loans_count = db.scalar(
        select(func.count(Loan.id)).where(
            Loan.agent_id == agent.id,
            Loan.status.in_(["repaid", "defaulted"]),
        )
    ) or 0

    own_records = task_count + resolved_loans_count

    if own_records < 5:
        principal_defaults = db.scalar(
            select(func.count(Loan.id))
            .join(Agent, Loan.agent_id == Agent.id)
            .where(
                Agent.principal_id == agent.principal_id,
                Loan.status == "defaulted",
            )
        ) or 0

        if principal_defaults >= 2:
            reasons.append(
                f"Name washing risk: agent has only {own_records} record(s) (< 5 required) "
                f"while principal '{agent.principal.name}' has {principal_defaults} default(s) (>= 2 threshold)"
            )

    return GateResult(passed=len(reasons) == 0, reasons=reasons)
