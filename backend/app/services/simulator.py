"""Deterministic Memory OFF vs Memory ON underwriting simulator.

Rounds are generated once from the seed and replayed against two independent
in-memory ledgers, so both modes see identical events. Simulator loans are
never written to the database.
"""

from __future__ import annotations

import json
import logging
import random
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import SessionLocal
from ..models import Agent
from . import memory, underwriter
from .scoring import LoanSample, TaskSample, compute_score

logger = logging.getLogger(__name__)

CATEGORIES = ("data-scraping", "report-writing", "code-review", "support-triage")
PATTERN_PRINCIPAL = "NovaOps"
PATTERN_CATEGORY = "data-scraping"
PATTERN_PROBABILITY = 0.75
OTHER_PROBABILITY = 0.06
FEE_RATE = 0.08
FORCED_PATTERN_SHARE = 0.35

BELIEF_QUESTION = (
    "What patterns have you learned about which agents, fleets and task "
    "categories default?"
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
CACHED_FILENAME = "cached_run.json"
FAKE_FILENAME = "fake_run.json"

EventCallback = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class AgentInfo:
    id: int
    name: str
    principal: str
    category: str
    tasks: tuple[TaskSample, ...]


class ModeLedger:
    """In-memory task and loan history for one simulation mode."""

    def __init__(
        self,
        tasks: Iterable[TaskSample] = (),
        loans: Iterable[LoanSample] = (),
    ) -> None:
        self.tasks = list(tasks)
        self.loans = [LoanSample(loan.status) for loan in loans]

    def add_loan(self, status: str) -> None:
        self.loans.append(LoanSample(status))

    def formula(self):
        return compute_score(self.tasks, self.loans)


@dataclass(frozen=True)
class FakeFact:
    principal: str
    category: str
    text: str
    is_default: bool


class FakeMemory:
    """Zero-network stand-in for Hindsight, used by fake mode and tests."""

    def __init__(self) -> None:
        self.facts: list[FakeFact] = []

    def recall(self, principal: str, category: str) -> tuple[list[str], float]:
        texts = [
            fact.text
            for fact in self.facts
            if fact.principal == principal and fact.category == category
        ]
        return texts, 0.0

    def retain_outcome(
        self,
        agent_name: str,
        principal: str,
        category: str,
        amount: float,
        outcome: str,
    ) -> None:
        is_default = outcome == "defaulted"
        verb = "DEFAULTED" if is_default else "REPAID in full"
        text = (
            f"Loan outcome: agent {agent_name} (principal {principal}, "
            f"category {category}) was lent ${amount:.0f} and {verb}."
        )
        self.facts.append(
            FakeFact(
                principal=principal,
                category=category,
                text=text,
                is_default=is_default,
            )
        )

    def reflect(self) -> str:
        defaults = sum(1 for fact in self.facts if fact.is_default)
        repayments = len(self.facts) - defaults
        return (
            f"Fake memory: {defaults} default(s) and {repayments} repayment(s) "
            "observed so far."
        )


def _load_agents() -> list[AgentInfo]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(Agent)
            .options(
                selectinload(Agent.principal),
                selectinload(Agent.task_records),
            )
            .order_by(Agent.id)
        ).all()

        agents = [
            AgentInfo(
                id=row.id,
                name=row.name,
                principal=row.principal.name,
                category=row.category,
                tasks=tuple(
                    TaskSample(task.success, task.amount)
                    for task in sorted(
                        row.task_records, key=lambda item: (item.ts, item.id)
                    )
                ),
            )
            for row in rows
        ]

    if not agents:
        raise RuntimeError("No agents found; run python -m app.seed first")
    return agents


def _precompute(
    agents: list[AgentInfo], rounds: int, seed: int
) -> tuple[dict[int, list[LoanSample]], list[dict[str, Any]]]:
    """Draw every random value before the loop (common random numbers)."""
    rng = random.Random(seed)

    synthetic: dict[int, list[LoanSample]] = {}
    for agent in agents:
        count = rng.randint(5, 8)
        synthetic[agent.id] = [
            LoanSample("repaid" if rng.random() < 0.95 else "defaulted")
            for _ in range(count)
        ]

    nova_agents = [agent for agent in agents if agent.principal == PATTERN_PRINCIPAL]
    forced_count = min(rounds, int(round(rounds * FORCED_PATTERN_SHARE)))
    forced_rounds = (
        set(rng.sample(range(1, rounds + 1), forced_count)) if nova_agents else set()
    )

    events: list[dict[str, Any]] = []
    for round_no in range(1, rounds + 1):
        forced = round_no in forced_rounds
        if forced:
            agent = rng.choice(nova_agents)
            category = PATTERN_CATEGORY
        else:
            agent = rng.choice(agents)
            category = rng.choice(CATEGORIES)

        events.append(
            {
                "round": round_no,
                "agent": agent,
                "category": category,
                "amount": float(rng.randrange(100, 301, 50)),
                "u": rng.random(),
                "forced_pattern": forced,
            }
        )

    return synthetic, events


def _default_probability(principal: str, category: str) -> float:
    if principal == PATTERN_PRINCIPAL and category == PATTERN_CATEGORY:
        return PATTERN_PROBABILITY
    return OTHER_PROBABILITY


def _ground_truth() -> dict[str, Any]:
    return {
        "rule": (
            "Default probability is 0.75 for NovaOps agents on data-scraping, "
            "otherwise 0.06."
        ),
        "novaops_data_scraping_default_probability": PATTERN_PROBABILITY,
        "other_default_probability": OTHER_PROBABILITY,
    }


def _fake_decision(
    fake_memory: FakeMemory,
    principal: str,
    category: str,
    amount: float,
    formula,
) -> tuple[float, float, str, int]:
    matching = [
        fact
        for fact in fake_memory.facts
        if fact.principal == principal and fact.category == category
    ]
    defaults = [fact for fact in matching if fact.is_default]

    if defaults:
        multiplier = 0.1
        rationale = (
            f"Fake memory: {len(defaults)} prior default(s) for {principal} "
            f"on {category}."
        )
    else:
        multiplier = 1.0
        rationale = "Fake memory: no matching defaults."

    final_limit = round(formula.formula_limit * multiplier, 2)
    return multiplier, final_limit, rationale, len(matching)


def _real_decision(
    bank_id: str,
    agent: AgentInfo,
    event: dict[str, Any],
    formula,
) -> tuple[float, float, str, int, float]:
    started = time.perf_counter()
    try:
        facts, _ = memory.recall_context(
            bank_id,
            agent.name,
            agent.principal,
            event["category"],
        )
        result = underwriter.decide(
            agent=agent.name,
            principal=agent.principal,
            category=event["category"],
            amount=event["amount"],
            formula=formula,
            memory_facts=facts,
            memory_on=True,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0

        if result.get("model") is None:
            return (
                1.0,
                float(formula.formula_limit),
                "fallback",
                len(facts),
                round(latency_ms, 1),
            )

        return (
            float(result["multiplier"]),
            float(result["final_limit"]),
            str(result.get("rationale") or ""),
            len(result.get("memory_facts") or facts),
            round(latency_ms, 1),
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.warning("Simulator ON fallback (%s)", type(exc).__name__)
        return (
            1.0,
            float(formula.formula_limit),
            "fallback",
            0,
            round(latency_ms, 1),
        )


def _process_round(
    mode: str,
    event: dict[str, Any],
    ledger: ModeLedger,
    p_default: float,
    cum_loss: float,
    cum_net: float,
    multiplier: float,
    formula_limit: float,
    final_limit: float,
    rationale: str,
    n_facts: int,
    latency_ms: float,
    fake_memory: FakeMemory | None,
    bank_id: str | None,
) -> tuple[dict[str, Any], float, float]:
    agent: AgentInfo = event["agent"]
    amount = float(event["amount"])
    u = float(event["u"])
    decision = "approved" if amount <= final_limit and final_limit > 0 else "denied"

    outcome: str | None = None
    loss = 0.0
    fee = 0.0

    if decision == "approved":
        if u < p_default:
            outcome = "defaulted"
            loss = amount
        else:
            outcome = "repaid"
            fee = round(amount * FEE_RATE, 2)

        ledger.add_loan(outcome)

        try:
            if mode == "on" and fake_memory is not None:
                fake_memory.retain_outcome(
                    agent.name,
                    agent.principal,
                    event["category"],
                    amount,
                    outcome,
                )
            elif mode == "on" and bank_id:
                memory.retain_outcome(
                    bank_id,
                    agent.name,
                    agent.principal,
                    event["category"],
                    amount,
                    outcome,
                    retain_async=False,
                )
        except Exception as exc:  # memory helpers are fail-safe, but never abort a run
            logger.warning("Simulator retain failed (%s)", type(exc).__name__)

    cum_loss = round(cum_loss + loss, 2)
    cum_net = round(cum_net + fee - loss, 2)

    row = {
        "round": event["round"],
        "agent": agent.name,
        "principal": agent.principal,
        "category": event["category"],
        "amount": amount,
        "formula_limit": float(formula_limit),
        "multiplier": round(multiplier, 4),
        "final_limit": float(final_limit),
        "decision": decision,
        "outcome": outcome,
        "loss": loss,
        "fee": fee,
        "cum_loss": cum_loss,
        "cum_net": cum_net,
        "rationale": rationale,
        "n_facts": n_facts,
        "latency_ms": latency_ms,
        "would_default": bool(u < p_default),
        "mode": mode,
    }
    return row, cum_loss, cum_net


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    approvals = sum(1 for row in rows if row["decision"] == "approved")
    total_loss = round(sum(row["loss"] for row in rows), 2)
    net_pnl = round(sum(row["fee"] - row["loss"] for row in rows), 2)
    avg_latency = (
        round(sum(row["latency_ms"] for row in rows) / len(rows), 1) if rows else 0.0
    )
    return {
        "total_loss": total_loss,
        "net_pnl": net_pnl,
        "approvals": approvals,
        "denials": len(rows) - approvals,
        "avg_latency_ms": avg_latency,
    }


def run_simulation(
    rounds: int = 40,
    seed: int = 7,
    fake: bool = False,
    run_id: str | None = None,
    on_event: EventCallback | None = None,
) -> dict[str, Any]:
    """Run both modes over identical events and return the full result."""
    if rounds < 1:
        raise ValueError("rounds must be at least 1")

    agents = _load_agents()
    synthetic, events = _precompute(agents, rounds, seed)

    off_ledgers = {
        agent.id: ModeLedger(agent.tasks, synthetic[agent.id]) for agent in agents
    }
    on_ledgers = {
        agent.id: ModeLedger(agent.tasks, synthetic[agent.id]) for agent in agents
    }

    run_id = run_id or uuid.uuid4().hex[:12]
    bank_id = None if fake else f"vouchai-sim-{run_id}"
    fake_memory = FakeMemory() if fake else None

    if bank_id:
        try:
            memory.ensure_bank(bank_id)
        except Exception as exc:
            logger.warning("Simulator ensure_bank failed (%s)", type(exc).__name__)

    off_rows: list[dict[str, Any]] = []
    on_rows: list[dict[str, Any]] = []
    beliefs: list[dict[str, Any]] = []
    cum_loss = {"off": 0.0, "on": 0.0}
    cum_net = {"off": 0.0, "on": 0.0}

    for event in events:
        agent: AgentInfo = event["agent"]
        p_default = _default_probability(agent.principal, event["category"])

        off_formula = off_ledgers[agent.id].formula()
        off_row, cum_loss["off"], cum_net["off"] = _process_round(
            "off",
            event,
            off_ledgers[agent.id],
            p_default,
            cum_loss["off"],
            cum_net["off"],
            1.0,
            float(off_formula.formula_limit),
            float(off_formula.formula_limit),
            "Formula only (memory off).",
            0,
            0.0,
            None,
            None,
        )

        on_formula = on_ledgers[agent.id].formula()
        if fake_memory is not None:
            multiplier, final_limit, rationale, n_facts = _fake_decision(
                fake_memory,
                agent.principal,
                event["category"],
                event["amount"],
                on_formula,
            )
            latency_ms = 0.0
        else:
            (
                multiplier,
                final_limit,
                rationale,
                n_facts,
                latency_ms,
            ) = _real_decision(bank_id or "", agent, event, on_formula)

        on_row, cum_loss["on"], cum_net["on"] = _process_round(
            "on",
            event,
            on_ledgers[agent.id],
            p_default,
            cum_loss["on"],
            cum_net["on"],
            multiplier,
            float(on_formula.formula_limit),
            final_limit,
            rationale,
            n_facts,
            latency_ms,
            fake_memory,
            bank_id,
        )

        off_rows.append(off_row)
        on_rows.append(on_row)
        if on_event is not None:
            on_event(
                "round",
                {
                    "round": event["round"],
                    "off": off_row,
                    "on": on_row,
                },
            )

        if event["round"] % 10 == 0:
            if fake_memory is not None:
                belief_text = fake_memory.reflect()
            else:
                belief_text = ""
                try:
                    belief_text = memory.reflect_beliefs(bank_id or "", BELIEF_QUESTION)
                except Exception as exc:
                    logger.warning(
                        "Simulator reflect failed (%s)", type(exc).__name__
                    )

            belief = {"after_round": event["round"], "text": belief_text}
            beliefs.append(belief)
            if on_event is not None:
                on_event("belief", belief)

    return {
        "mode": "fake" if fake else "real",
        "run_id": run_id,
        "seed": seed,
        "rounds": rounds,
        "ground_truth": _ground_truth(),
        "off": off_rows,
        "on": on_rows,
        "beliefs": beliefs,
        "summary": {
            "off": _summarize(off_rows),
            "on": _summarize(on_rows),
        },
    }


def result_path(result: dict[str, Any], data_dir: Path | str | None = None) -> Path:
    """Return the file a result belongs to; fake runs never target cached."""
    target = Path(data_dir) if data_dir is not None else DATA_DIR
    filename = FAKE_FILENAME if result.get("mode") == "fake" else CACHED_FILENAME
    return target / filename


def save_result(
    result: dict[str, Any], data_dir: Path | str | None = None
) -> Path:
    """Persist a run, routing fake runs away from cached_run.json."""
    path = result_path(result, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return path
