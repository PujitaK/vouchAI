"""SQLAlchemy ORM models for principals, agents, task records, and loans."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp used for model defaults."""
    return datetime.now(timezone.utc)


class Principal(Base):
    __tablename__ = "principals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    agents: Mapped[list["Agent"]] = relationship(back_populates="principal")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    principal_id: Mapped[int] = mapped_column(ForeignKey("principals.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    principal: Mapped[Principal] = relationship(back_populates="agents")
    task_records: Mapped[list["TaskRecord"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    loans: Mapped[list["Loan"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class TaskRecord(Base):
    __tablename__ = "task_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    success: Mapped[bool] = mapped_column(nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    agent: Mapped[Agent] = relationship(back_populates="task_records")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)
    formula_limit: Mapped[float] = mapped_column(Float, nullable=False)
    final_limit: Mapped[float] = mapped_column(Float, nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    memory_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    memory_facts: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    agent: Mapped[Agent] = relationship(back_populates="loans")
