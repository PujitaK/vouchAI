"""CSV import endpoints for tasks and loans."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import verify_admin_key
from ..db import get_db
from ..models import Agent, Loan, Principal, TaskRecord, utcnow
from ..services import memory

router = APIRouter(prefix="/import", tags=["import"], dependencies=[Depends(verify_admin_key)])

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
DEFAULT_BANK_ID = "vouchai-lender-main"


def _read_and_validate_file(file: UploadFile) -> str:
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum limit of 2 MB",
        )
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        ) from exc


def _get_or_create_principal(db: Session, name: str, cache: dict[str, Principal]) -> Principal:
    if name in cache:
        return cache[name]
    principal = db.scalar(select(Principal).where(Principal.name == name))
    if principal is None:
        principal = Principal(name=name)
        db.add(principal)
        db.flush()
    cache[name] = principal
    return principal


@router.post("/tasks")
def import_tasks(
    file: UploadFile = File(...),
    replace: bool = Query(False, description="Clear existing data before import (local use only)"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    text = _read_and_validate_file(file)

    if replace:
        db.query(Loan).delete()
        db.query(TaskRecord).delete()
        db.query(Agent).delete()
        db.query(Principal).delete()
        db.commit()

    reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )

    headers = [h.strip().lower() for h in header_row]
    col_map = {name: idx for idx, name in enumerate(headers)}
    required = ["agent", "principal", "category", "success", "amount"]
    missing = [c for c in required if c not in col_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    principals_cache: dict[str, Principal] = {}
    agents_cache: dict[str, Agent] = {}
    for agent in db.scalars(select(Agent)).all():
        agents_cache[agent.name] = agent

    added_count = 0
    rejected: list[dict[str, Any]] = []
    total_rows = 0

    for line_num, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        total_rows += 1

        if len(row) <= max(col_map[c] for c in required):
            rejected.append({"line": line_num, "reason": "Missing column values in row"})
            continue

        agent_name = row[col_map["agent"]].strip()
        principal_name = row[col_map["principal"]].strip()
        category = row[col_map["category"]].strip()
        success_str = row[col_map["success"]].strip().lower()
        amount_str = row[col_map["amount"]].strip()

        if not agent_name or not principal_name or not category:
            rejected.append({"line": line_num, "reason": "Agent, principal, and category must not be empty"})
            continue

        if success_str in ("true", "1"):
            success = True
        elif success_str in ("false", "0"):
            success = False
        else:
            rejected.append({"line": line_num, "reason": "success must be true or false"})
            continue

        try:
            amount = float(amount_str)
            if amount <= 0:
                rejected.append({"line": line_num, "reason": "amount must be greater than 0"})
                continue
        except ValueError:
            rejected.append({"line": line_num, "reason": "amount must be a valid number"})
            continue

        ts = utcnow()
        if "ts" in col_map and col_map["ts"] < len(row):
            ts_str = row[col_map["ts"]].strip()
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                except ValueError:
                    rejected.append({"line": line_num, "reason": "Invalid timestamp format"})
                    continue

        # Identity check: agent name must never belong to a different principal
        existing_agent = agents_cache.get(agent_name)
        if existing_agent is not None:
            if existing_agent.principal.name != principal_name:
                rejected.append({
                    "line": line_num,
                    "reason": f"Identity conflict: agent '{agent_name}' belongs to principal '{existing_agent.principal.name}', not '{principal_name}'",
                })
                continue
        else:
            principal = _get_or_create_principal(db, principal_name, principals_cache)
            agent = Agent(
                name=agent_name,
                principal_id=principal.id,
                category=category,
            )
            db.add(agent)
            db.flush()
            agent.principal = principal
            agents_cache[agent_name] = agent
            existing_agent = agent

        task = TaskRecord(
            agent_id=existing_agent.id,
            success=success,
            amount=amount,
            ts=ts,
        )
        db.add(task)
        added_count += 1

    db.commit()
    return {
        "added": added_count,
        "rejected": rejected,
        "total": total_rows,
    }


@router.post("/loans")
def import_loans(
    file: UploadFile = File(...),
    teach_memory: bool = Query(True, description="Record outcomes to Hindsight memory"),
    bank_id: str = Query(DEFAULT_BANK_ID),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    text = _read_and_validate_file(file)

    reader = csv.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )

    headers = [h.strip().lower() for h in header_row]
    col_map = {name: idx for idx, name in enumerate(headers)}
    required = ["agent", "principal", "category", "amount", "outcome"]
    missing = [c for c in required if c not in col_map]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(missing)}",
        )

    principals_cache: dict[str, Principal] = {}
    agents_cache: dict[str, Agent] = {}
    for agent in db.scalars(select(Agent)).all():
        agents_cache[agent.name] = agent

    added_count = 0
    rejected: list[dict[str, Any]] = []
    total_rows = 0

    if teach_memory:
        memory.ensure_bank(bank_id)

    for line_num, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        total_rows += 1

        if len(row) <= max(col_map[c] for c in required):
            rejected.append({"line": line_num, "reason": "Missing column values in row"})
            continue

        agent_name = row[col_map["agent"]].strip()
        principal_name = row[col_map["principal"]].strip()
        category = row[col_map["category"]].strip()
        amount_str = row[col_map["amount"]].strip()
        outcome_str = row[col_map["outcome"]].strip().lower()

        if not agent_name or not principal_name or not category:
            rejected.append({"line": line_num, "reason": "Agent, principal, and category must not be empty"})
            continue

        try:
            amount = float(amount_str)
            if amount <= 0:
                rejected.append({"line": line_num, "reason": "amount must be greater than 0"})
                continue
        except ValueError:
            rejected.append({"line": line_num, "reason": "amount must be a valid number"})
            continue

        if outcome_str not in ("repaid", "defaulted"):
            rejected.append({"line": line_num, "reason": "outcome must be 'repaid' or 'defaulted'"})
            continue

        # Identity check: agent name must never belong to a different principal
        existing_agent = agents_cache.get(agent_name)
        if existing_agent is not None:
            if existing_agent.principal.name != principal_name:
                rejected.append({
                    "line": line_num,
                    "reason": f"Identity conflict: agent '{agent_name}' belongs to principal '{existing_agent.principal.name}', not '{principal_name}'",
                })
                continue
        else:
            principal = _get_or_create_principal(db, principal_name, principals_cache)
            agent = Agent(
                name=agent_name,
                principal_id=principal.id,
                category=category,
            )
            db.add(agent)
            db.flush()
            agent.principal = principal
            agents_cache[agent_name] = agent
            existing_agent = agent

        loan = Loan(
            agent_id=existing_agent.id,
            requested_amount=amount,
            formula_limit=amount,
            final_limit=amount,
            multiplier=1.0,
            memory_used=teach_memory,
            memory_facts="[]",
            decision="approved",
            rationale="Imported historical loan",
            status=outcome_str,
            created_at=utcnow(),
            resolved_at=utcnow(),
        )
        db.add(loan)
        added_count += 1

        if teach_memory:
            memory.retain_outcome(
                bank_id=bank_id,
                agent_name=existing_agent.name,
                principal_name=existing_agent.principal.name,
                category=category,
                amount=amount,
                outcome=outcome_str,
            )

    db.commit()
    return {
        "added": added_count,
        "rejected": rejected,
        "total": total_rows,
    }
