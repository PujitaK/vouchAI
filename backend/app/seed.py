"""Idempotent demo data seed.

Run from the backend directory:

    python -m app.seed
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from .db import SessionLocal, init_db
from .models import Agent, Principal, TaskRecord

PRINCIPALS = ("NovaOps", "LedgerLeaf", "Quanta Works", "BlueHarbor")

# (agent name, principal, category)
AGENTS = (
    ("scraper-07", "NovaOps", "data-scraping"),
    ("summarizer-12", "NovaOps", "report-writing"),
    ("reviewer-03", "NovaOps", "code-review"),
    ("scraper-11", "LedgerLeaf", "data-scraping"),
    ("summarizer-05", "LedgerLeaf", "report-writing"),
    ("triage-02", "LedgerLeaf", "support-triage"),
    ("reviewer-08", "Quanta Works", "code-review"),
    ("triage-06", "Quanta Works", "support-triage"),
    ("scraper-02", "Quanta Works", "data-scraping"),
    ("summarizer-04", "BlueHarbor", "report-writing"),
    ("reviewer-11", "BlueHarbor", "code-review"),
    ("triage-09", "BlueHarbor", "support-triage"),
)


def seed() -> None:
    init_db()
    rng = random.Random(20240517)
    now = datetime.now(timezone.utc)

    created_agents = 0
    created_tasks = 0

    with SessionLocal() as db:
        for name in PRINCIPALS:
            if db.scalar(select(Principal).where(Principal.name == name)) is None:
                db.add(Principal(name=name))
        db.flush()

        principals = {
            principal.name: principal for principal in db.scalars(select(Principal)).all()
        }

        for name, principal_name, category in AGENTS:
            agent = db.scalar(select(Agent).where(Agent.name == name))
            if agent is None:
                agent = Agent(
                    name=name,
                    principal_id=principals[principal_name].id,
                    category=category,
                )
                db.add(agent)
                db.flush()
                created_agents += 1

            has_tasks = db.scalar(
                select(TaskRecord.id).where(TaskRecord.agent_id == agent.id).limit(1)
            )
            if has_tasks is not None:
                continue

            for _ in range(rng.randint(10, 25)):
                db.add(
                    TaskRecord(
                        agent_id=agent.id,
                        success=rng.random() < 0.85,
                        amount=round(rng.uniform(20, 300), 2),
                        ts=now - timedelta(days=rng.uniform(0, 60)),
                    )
                )
                created_tasks += 1

        db.commit()

        total_principals = db.scalar(select(func.count()).select_from(Principal))
        total_agents = db.scalar(select(func.count()).select_from(Agent))
        total_tasks = db.scalar(select(func.count()).select_from(TaskRecord))

    print(
        "Seed complete: "
        f"{total_principals} principals, {total_agents} agents, {total_tasks} task records "
        f"(added {created_agents} agents, {created_tasks} task records this run)."
    )


if __name__ == "__main__":
    seed()
