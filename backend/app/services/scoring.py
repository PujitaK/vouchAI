"""Pure, database-free underwriting score math.

The routers convert ORM rows into the small sample dataclasses below, so the
math here can be unit tested without a session or an app.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence

WINDOW = 20
COLD_START_RECORDS = 5
RESOLVED_STATUSES = frozenset({"repaid", "defaulted"})


@dataclass(frozen=True)
class TaskSample:
    """One completed task, newest last."""

    success: bool
    amount: float


@dataclass(frozen=True)
class LoanSample:
    """One loan; only repaid/defaulted loans affect repayment history."""

    status: str


@dataclass(frozen=True)
class ScoreBreakdown:
    score: float
    confidence: float
    components: dict[str, float]
    formula_limit: int


def _recent(tasks: Sequence[TaskSample]) -> list[TaskSample]:
    return list(tasks)[-WINDOW:]


def task_success_rate(tasks: Sequence[TaskSample]) -> float:
    """Success rate (0-100) over the last 20 task records."""
    recent = _recent(tasks)
    if not recent:
        return 0.0
    return sum(1 for task in recent if task.success) / len(recent) * 100.0


def spend_regularity(tasks: Sequence[TaskSample]) -> float:
    """100 minus the coefficient of variation of amounts, floored at 0."""
    amounts = [task.amount for task in _recent(tasks)]
    if len(amounts) < 3:
        return 50.0
    mean = statistics.fmean(amounts)
    if mean == 0:
        return 50.0
    coefficient = statistics.pstdev(amounts) / mean
    return 100.0 - min(100.0, coefficient * 100.0)


def resolved_loans(loans: Sequence[LoanSample]) -> list[LoanSample]:
    return [loan for loan in loans if loan.status in RESOLVED_STATUSES]


def repayment_history(loans: Sequence[LoanSample]) -> float:
    """Repaid / (repaid + defaulted) as a percentage, 50 if no history."""
    resolved = resolved_loans(loans)
    if not resolved:
        return 50.0
    repaid = sum(1 for loan in resolved if loan.status == "repaid")
    return repaid / len(resolved) * 100.0


def limit_for_score(score: float, records: int) -> int:
    """Map a score and record count to the formula limit."""
    if records < COLD_START_RECORDS:
        return 50
    if score < 40:
        return 0
    if score < 60:
        return 100
    if score < 80:
        return 300
    return 600


def compute_score(
    tasks: Sequence[TaskSample], loans: Sequence[LoanSample]
) -> ScoreBreakdown:
    """Blend the three metrics with a confidence weight toward 40."""
    tasks = list(tasks)
    loans = list(loans)

    success = task_success_rate(tasks)
    regularity = spend_regularity(tasks)
    repayment = repayment_history(loans)

    raw = 0.35 * success + 0.15 * regularity + 0.50 * repayment

    resolved = resolved_loans(loans)
    records = len(tasks) + len(resolved)
    confidence = min(records / WINDOW, 1.0)
    score = confidence * raw + (1.0 - confidence) * 40.0

    # Poor repayment record hard-caps the blended score.
    if resolved:
        repaid = sum(1 for loan in resolved if loan.status == "repaid")
        if repaid / len(resolved) < 0.5:
            score = min(score, 40.0)

    return ScoreBreakdown(
        score=round(score, 2),
        confidence=round(confidence, 4),
        components={
            "task_success": round(success, 2),
            "spend_regularity": round(regularity, 2),
            "repayment_history": round(repayment, 2),
            "raw": round(raw, 2),
        },
        formula_limit=limit_for_score(score, records),
    )
