"""Offline simulator tests (fake mode, no network calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal  # noqa: E402
from app.models import Agent, Loan  # noqa: E402
from app.seed import seed  # noqa: E402
from app.services import simulator  # noqa: E402
from app.services.scoring import LoanSample, TaskSample  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def ensure_seeded() -> None:
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Agent))
    if not count:
        seed()


def _run(rounds: int = 40, seed_value: int = 7, run_id: str = "test") -> dict:
    return simulator.run_simulation(
        rounds=rounds,
        seed=seed_value,
        fake=True,
        run_id=run_id,
    )


def test_same_seed_gives_identical_results() -> None:
    first = _run(rounds=16, run_id="fixed")
    second = _run(rounds=16, run_id="fixed")

    assert first["mode"] == "fake"
    assert first["off"] == second["off"]
    assert first["on"] == second["on"]
    assert first["beliefs"] == second["beliefs"]
    assert first["summary"] == second["summary"]
    assert first["ground_truth"] == second["ground_truth"]
    assert (
        first["ground_truth"]["novaops_data_scraping_default_probability"] == 0.75
    )
    assert first["ground_truth"]["other_default_probability"] == 0.06


def test_off_and_on_see_the_same_events() -> None:
    result = _run(rounds=20, run_id="events")

    assert len(result["off"]) == 20
    assert len(result["on"]) == 20
    for off, on in zip(result["off"], result["on"]):
        for key in (
            "round",
            "agent",
            "principal",
            "category",
            "amount",
            "would_default",
        ):
            assert off[key] == on[key]


def test_fake_memory_reduces_total_loss() -> None:
    result = _run(rounds=40, run_id="loss")

    assert result["summary"]["on"]["total_loss"] < result["summary"]["off"][
        "total_loss"
    ]


def test_ledger_updates_change_the_formula() -> None:
    ledger = simulator.ModeLedger(
        tasks=[TaskSample(True, 100.0) for _ in range(20)],
        loans=[LoanSample("repaid") for _ in range(5)],
    )
    before = ledger.formula()

    for _ in range(6):
        ledger.add_loan("defaulted")

    after = ledger.formula()

    assert after.score < before.score
    assert after.formula_limit < before.formula_limit


def test_fake_save_never_overwrites_cached(tmp_path: Path) -> None:
    cached = tmp_path / "cached_run.json"
    cached.write_text('{"sentinel": true}', encoding="utf-8")

    path = simulator.save_result({"mode": "fake", "ok": True}, data_dir=tmp_path)

    assert path.name == "fake_run.json"
    assert json.loads(cached.read_text(encoding="utf-8")) == {"sentinel": True}
    assert json.loads(path.read_text(encoding="utf-8")) == {"mode": "fake", "ok": True}


def test_real_save_uses_cached_file(tmp_path: Path) -> None:
    path = simulator.save_result({"mode": "real"}, data_dir=tmp_path)

    assert path.name == "cached_run.json"
    assert json.loads(path.read_text(encoding="utf-8"))["mode"] == "real"


def test_fake_run_does_not_write_simulator_loans() -> None:
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(Loan))

    _run(rounds=12, run_id="readonly")

    with SessionLocal() as db:
        after = db.scalar(select(func.count()).select_from(Loan))

    assert after == before
