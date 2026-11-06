"""Offline tests for identity gating (no network calls)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, Loan, Principal, TaskRecord  # noqa: E402
from app.services.identity import check_identity, normalize_name  # noqa: E402


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_normalize_name():
    assert normalize_name("Scraper-07") == "scraper07"
    assert normalize_name("Alpha_Bot.123") == "alphabot123"
    assert normalize_name("  Nova Ops!  ") == "novaops"


def test_clean_new_agent_passes(db):
    uid = uuid.uuid4().hex[:6]
    principal = Principal(name=f"CleanFleet-{uid}")
    db.add(principal)
    db.flush()

    agent = Agent(
        name=f"clean-worker-{uid}",
        principal_id=principal.id,
        category="data-scraping",
    )
    db.add(agent)
    db.flush()

    # Clean agent with 0 defaults passes
    result = check_identity(db, agent)
    assert result.passed is True
    assert result.reasons == []

    # Clean agent with 5 tasks passes
    for i in range(5):
        db.add(TaskRecord(agent_id=agent.id, success=True, amount=100.0))
    db.commit()

    result_after = check_identity(db, agent)
    assert result_after.passed is True
    assert result_after.reasons == []


def test_lookalike_name_blocked(db):
    uid = uuid.uuid4().hex[:6]
    p1 = Principal(name=f"FleetOne-{uid}")
    p2 = Principal(name=f"FleetTwo-{uid}")
    db.add_all([p1, p2])
    db.flush()

    # Legitimate agent under FleetOne
    agent1 = Agent(name=f"bot-alpha-{uid}", principal_id=p1.id, category="report-writing")
    db.add(agent1)
    db.flush()

    # Lookalike impersonator under FleetTwo (different punctuation, same normalized string)
    agent2 = Agent(name=f"botalpha{uid}", principal_id=p2.id, category="report-writing")
    db.add(agent2)
    db.flush()

    result = check_identity(db, agent2)
    assert result.passed is False
    assert any("Lookalike identity conflict" in r for r in result.reasons)

    # Agent under the same principal does not trigger lookalike against itself
    result_same = check_identity(db, agent1)
    # agent1 checks against others; agent2 is under p2 so agent1 also sees agent2 as a conflict
    assert result_same.passed is False


def test_name_washing_blocked(db):
    uid = uuid.uuid4().hex[:6]
    principal = Principal(name=f"DefaultingFleet-{uid}")
    db.add(principal)
    db.flush()

    # Agent with 2 defaulted loans under this principal
    tainted_agent = Agent(name=f"tainted-{uid}", principal_id=principal.id, category="code-review")
    db.add(tainted_agent)
    db.flush()

    loan1 = Loan(
        agent_id=tainted_agent.id,
        requested_amount=100.0,
        formula_limit=100.0,
        final_limit=100.0,
        decision="approved",
        rationale="Seed loan",
        status="defaulted",
    )
    loan2 = Loan(
        agent_id=tainted_agent.id,
        requested_amount=150.0,
        formula_limit=150.0,
        final_limit=150.0,
        decision="approved",
        rationale="Seed loan 2",
        status="defaulted",
    )
    db.add_all([loan1, loan2])
    db.commit()

    # Brand new agent with only 2 records (< 5) under the defaulting principal
    fresh_agent = Agent(name=f"fresh-{uid}", principal_id=principal.id, category="code-review")
    db.add(fresh_agent)
    db.flush()

    db.add(TaskRecord(agent_id=fresh_agent.id, success=True, amount=50.0))
    db.add(TaskRecord(agent_id=fresh_agent.id, success=True, amount=50.0))
    db.commit()

    result = check_identity(db, fresh_agent)
    assert result.passed is False
    assert any("Name washing risk" in r for r in result.reasons)

    # Once agent reaches 5 records, name washing rule does not block it
    for _ in range(3):
        db.add(TaskRecord(agent_id=fresh_agent.id, success=True, amount=50.0))
    db.commit()

    result_established = check_identity(db, fresh_agent)
    assert result_established.passed is True


def test_loan_endpoint_blocks_identity_gate(monkeypatch, db):
    uid = uuid.uuid4().hex[:6]
    p1 = Principal(name=f"P1-{uid}")
    p2 = Principal(name=f"P2-{uid}")
    db.add_all([p1, p2])
    db.flush()

    legit = Agent(name=f"crawler-{uid}", principal_id=p1.id, category="data-scraping")
    db.add(legit)
    db.flush()

    impersonator = Agent(name=f"crawler{uid}", principal_id=p2.id, category="data-scraping")
    db.add(impersonator)
    db.commit()

    # Ensure memory and underwriter are NOT called
    called = {"memory": False, "underwriter": False}

    def fake_recall(*args, **kwargs):
        called["memory"] = True
        return [], 0.0

    def fake_decide(*args, **kwargs):
        called["underwriter"] = True
        return {}

    monkeypatch.setattr("app.services.memory.recall_context", fake_recall)
    monkeypatch.setattr("app.services.underwriter.decide", fake_decide)

    client = TestClient(app)
    response = client.post(
        f"/loans/{impersonator.id}",
        json={
            "amount": 200.0,
            "purpose": "Scale compute",
            "use_memory": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "denied"
    assert data["status"] == "denied"
    assert data["identity_blocked"] is True
    assert "Identity gate:" in data["rationale"]
    assert called["memory"] is False
    assert called["underwriter"] is False
