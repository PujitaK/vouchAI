"""Offline tests for CSV imports and ADMIN_KEY protection (no network calls)."""

from __future__ import annotations

import io
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, Loan, Principal, TaskRecord  # noqa: E402


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_import_tasks_saves_good_rows_and_rejects_bad():
    uid = uuid.uuid4().hex[:6]
    client = TestClient(app)

    csv_content = f"""agent,principal,category,success,amount,ts
worker1-{uid},FleetA-{uid},data-scraping,true,100.50,2026-03-01T10:00:00Z
worker1-{uid},FleetA-{uid},data-scraping,false,75.00,
worker2-{uid},FleetA-{uid},report-writing,NOT_A_BOOL,50.00,2026-03-01T10:00:00Z
worker3-{uid},FleetA-{uid},data-scraping,true,-20.00,2026-03-01T10:00:00Z
"""
    files = {"file": ("tasks.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/import/tasks", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 2
    assert len(data["rejected"]) == 2
    assert data["total"] == 4

    rejection_reasons = [r["reason"] for r in data["rejected"]]
    assert any("success must be true or false" in r for r in rejection_reasons)
    assert any("amount must be greater than 0" in r for r in rejection_reasons)

    with SessionLocal() as db:
        agent = db.scalar(select(Agent).where(Agent.name == f"worker1-{uid}"))
        assert agent is not None
        assert len(agent.task_records) == 2
        # worker2 and worker3 had only bad rows, should not have tasks
        bad_agent2 = db.scalar(select(Agent).where(Agent.name == f"worker2-{uid}"))
        assert bad_agent2 is None


def test_import_loans_saves_good_rows_and_rejects_bad(monkeypatch):
    uid = uuid.uuid4().hex[:6]
    client = TestClient(app)

    # Mock memory retain to avoid external calls
    retained_facts = []

    def fake_retain(*args, **kwargs):
        retained_facts.append(kwargs)
        return True

    monkeypatch.setattr("app.services.memory.retain_outcome", fake_retain)
    monkeypatch.setattr("app.services.memory.ensure_bank", lambda *args, **kwargs: True)

    csv_content = f"""agent,principal,category,amount,outcome
borrower1-{uid},FleetL-{uid},data-scraping,300.00,repaid
borrower2-{uid},FleetL-{uid},data-scraping,450.00,defaulted
borrower3-{uid},FleetL-{uid},code-review,0.00,repaid
borrower4-{uid},FleetL-{uid},code-review,100.00,unrecognized_status
"""
    files = {"file": ("loans.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/import/loans?teach_memory=true", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["added"] == 2
    assert len(data["rejected"]) == 2
    assert data["total"] == 4

    with SessionLocal() as db:
        b1 = db.scalar(select(Agent).where(Agent.name == f"borrower1-{uid}"))
        assert b1 is not None
        assert len(b1.loans) == 1
        assert b1.loans[0].status == "repaid"

        b2 = db.scalar(select(Agent).where(Agent.name == f"borrower2-{uid}"))
        assert b2 is not None
        assert len(b2.loans) == 1
        assert b2.loans[0].status == "defaulted"


def test_identity_conflict_rejected():
    uid = uuid.uuid4().hex[:6]
    client = TestClient(app)

    # First, import agent under PrincipalOne
    csv_1 = f"""agent,principal,category,success,amount
unique-agent-{uid},PrincipalOne-{uid},data-scraping,true,100.00
"""
    res1 = client.post(
        "/import/tasks",
        files={"file": ("tasks.csv", io.BytesIO(csv_1.encode("utf-8")), "text/csv")},
    )
    assert res1.status_code == 200
    assert res1.json()["added"] == 1

    # Second, attempt to import the same agent under PrincipalTwo
    csv_conflict = f"""agent,principal,category,success,amount
unique-agent-{uid},PrincipalTwo-{uid},data-scraping,true,200.00
"""
    res2 = client.post(
        "/import/tasks",
        files={"file": ("tasks.csv", io.BytesIO(csv_conflict.encode("utf-8")), "text/csv")},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["added"] == 0
    assert len(data2["rejected"]) == 1
    assert "Identity conflict:" in data2["rejected"][0]["reason"]
    assert f"PrincipalOne-{uid}" in data2["rejected"][0]["reason"]


def test_wrong_api_key_gets_401_when_admin_key_is_set(monkeypatch):
    client = TestClient(app)

    # Set ADMIN_KEY
    monkeypatch.setenv("ADMIN_KEY", "super-secret-key-123")

    csv_data = b"agent,principal,category,success,amount\na,p,c,true,10"
    files = {"file": ("tasks.csv", io.BytesIO(csv_data), "text/csv")}

    # 1. Missing header -> 401
    res_no_key = client.post("/import/tasks", files=files)
    assert res_no_key.status_code == 401
    assert res_no_key.json()["detail"] == "Invalid or missing API key"

    # 2. Wrong header -> 401
    files = {"file": ("tasks.csv", io.BytesIO(csv_data), "text/csv")}
    res_wrong_key = client.post(
        "/import/tasks",
        files=files,
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_wrong_key.status_code == 401

    # 3. Protected /sim/run with wrong key -> 401
    res_sim = client.post("/sim/run", headers={"X-API-Key": "wrong-key"})
    assert res_sim.status_code == 401

    # 4. Protected /loans/1/resolve with wrong key -> 401
    res_resolve = client.post(
        "/loans/1/resolve",
        json={"outcome": "repaid"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_resolve.status_code == 401

    # 5. Valid key -> allowed (e.g. 200 on /import/tasks)
    files = {"file": ("tasks.csv", io.BytesIO(csv_data), "text/csv")}
    res_valid = client.post(
        "/import/tasks",
        files=files,
        headers={"X-API-Key": "super-secret-key-123"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["added"] == 1
