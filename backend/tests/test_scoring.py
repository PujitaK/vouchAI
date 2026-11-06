"""Unit tests for the pure scoring math."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.scoring import (  # noqa: E402
    LoanSample,
    TaskSample,
    compute_score,
    limit_for_score,
    repayment_history,
    spend_regularity,
    task_success_rate,
)


def tasks(successes: list[bool], amount: float = 100.0) -> list[TaskSample]:
    return [TaskSample(success=ok, amount=amount) for ok in successes]


def test_cold_start_gives_limit_50() -> None:
    result = compute_score(tasks([True, True, False]), [])
    assert result.formula_limit == 50
    assert result.confidence == pytest.approx(3 / 20)


def test_cold_start_ignores_good_score() -> None:
    assert limit_for_score(100.0, 4) == 50
    assert limit_for_score(100.0, 5) == 600


def test_repayment_cap_at_40() -> None:
    # 20 successes with steady amounts -> raw = 35 + 15 + 20 = 70.
    history = [LoanSample("repaid"), LoanSample("repaid")] + [
        LoanSample("defaulted"),
        LoanSample("defaulted"),
        LoanSample("defaulted"),
    ]
    result = compute_score(tasks([True] * 20), history)

    assert repayment_history(history) == pytest.approx(40.0)
    assert result.components["raw"] == pytest.approx(70.0)
    assert result.score == 40.0
    assert result.formula_limit == 100


def test_confidence_blending() -> None:
    result = compute_score(tasks([True] * 10), [])

    assert result.confidence == 0.5
    assert result.components["raw"] == pytest.approx(75.0)
    assert result.score == pytest.approx(57.5)


def test_full_confidence_reaches_raw_score() -> None:
    # 35 + 15 + 25 (neutral repayment) = 75 with confidence 1.0.
    result = compute_score(tasks([True] * 20), [])
    assert result.confidence == 1.0
    assert result.score == pytest.approx(75.0)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, 0),
        (39.99, 0),
        (40.0, 100),
        (59.99, 100),
        (60.0, 300),
        (79.99, 300),
        (80.0, 600),
        (100.0, 600),
    ],
)
def test_tier_boundaries(score: float, expected: int) -> None:
    assert limit_for_score(score, 10) == expected


def test_spend_regularity_defaults_with_fewer_than_three() -> None:
    assert spend_regularity(tasks([True, True])) == 50.0


def test_spend_regularity_is_100_for_constant_amounts() -> None:
    assert spend_regularity(tasks([True] * 5, amount=50.0)) == 100.0


def test_repayment_history_defaults_without_resolved_loans() -> None:
    assert repayment_history([]) == 50.0
    assert repayment_history([LoanSample("active")]) == 50.0


def test_success_rate_uses_last_twenty_records() -> None:
    oldest_failures = tasks([False] * 5)
    recent_successes = tasks([True] * 20)
    assert task_success_rate(oldest_failures + recent_successes) == 100.0
