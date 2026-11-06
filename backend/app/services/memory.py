"""Hindsight-backed memory for the VouchAI underwriter.

All calls are best-effort: one retry, then a fail-safe empty result with a
warning. API keys are read from the environment and never logged.
"""

from __future__ import annotations

import atexit
import logging
import os
import time
from pathlib import Path
from typing import Callable, TypeVar

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)

MISSION = (
    "I am a lending underwriter for autonomous AI agents. I learn which agents, "
    "principal fleets and task categories repay or default, and I form beliefs "
    "from outcomes."
)

_T = TypeVar("_T")

_client: Hindsight | None = None


def _get_client() -> Hindsight:
    """Lazily create and reuse one Hindsight client."""
    global _client
    if _client is None:
        base_url = os.getenv("HINDSIGHT_BASE_URL")
        api_key = os.getenv("HINDSIGHT_API_KEY")
        if not base_url or not api_key:
            raise RuntimeError("Hindsight credentials are not configured")
        _client = Hindsight(base_url=base_url, api_key=api_key, timeout=60.0)
        atexit.register(_close_client)
    return _client


def _close_client() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        except Exception as exc:  # pragma: no cover - shutdown best effort
            logger.warning("Hindsight client close failed (%s)", type(exc).__name__)
        _client = None


def _run(label: str, action: Callable[[], _T], fallback: _T) -> tuple[_T, float]:
    """Run an action once, retry once, then return fallback."""
    started = time.perf_counter()
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = action()
            latency_ms = (time.perf_counter() - started) * 1000.0
            if attempt > 0:
                logger.info("%s succeeded on retry in %.1f ms", label, latency_ms)
            return result, latency_ms
        except Exception as exc:
            last_error = exc
            logger.debug("%s attempt %d failed (%s)", label, attempt + 1, type(exc).__name__)

    latency_ms = (time.perf_counter() - started) * 1000.0
    logger.warning(
        "%s failed after 2 attempts in %.1f ms (%s)",
        label,
        latency_ms,
        type(last_error).__name__ if last_error else "unknown",
    )
    return fallback, latency_ms


def ensure_bank(bank_id: str) -> bool:
    """Create the memory bank if needed; existing banks are not an error."""
    created, _ = _run(
        "ensure_bank",
        lambda: bool(
            _get_client().create_bank(
                bank_id=bank_id,
                name=bank_id,
                mission=MISSION,
            )
        ),
        False,
    )
    return created


def retain_outcome(
    bank_id: str,
    agent_name: str,
    principal_name: str,
    category: str,
    amount: float,
    outcome: str,
    round_no: int | None = None,
    retain_async: bool = False,
) -> bool:
    """Remember whether an agent repaid or defaulted on a loan."""
    normalized = outcome.strip().lower()
    if "repaid" in normalized:
        verb = "REPAID in full"
    elif "default" in normalized:
        verb = "DEFAULTED"
    else:
        verb = outcome.strip().upper()

    content = (
        f"Loan outcome: agent {agent_name} (principal {principal_name}, "
        f"category {category}) was lent ${amount:.0f} and {verb}."
    )
    if round_no is not None:
        content = f"Round {round_no}. {content}"

    retained, _ = _run(
        "retain_outcome",
        lambda: bool(
            _get_client().retain(
                bank_id=bank_id,
                content=content,
                context="loan outcome",
                tags=[principal_name, category],
                retain_async=retain_async,
            )
        ),
        False,
    )
    return retained


def retain_decision(
    bank_id: str,
    agent_name: str,
    principal_name: str,
    category: str,
    amount: float,
    decision: str,
    rationale: str,
    round_no: int | None = None,
    retain_async: bool = False,
) -> bool:
    """Remember the underwriter's own decision and why it made it."""
    rationale_text = rationale.strip().rstrip(".") or "no rationale supplied"
    content = (
        f"Underwriting decision: {decision.upper()} a ${amount:.0f} loan to agent "
        f"{agent_name} (principal {principal_name}, category {category}); "
        f"rationale: {rationale_text}."
    )
    if round_no is not None:
        content = f"Round {round_no}. {content}"

    retained, _ = _run(
        "retain_decision",
        lambda: bool(
            _get_client().retain(
                bank_id=bank_id,
                content=content,
                context="underwriting decision",
                tags=[principal_name, category],
                retain_async=retain_async,
            )
        ),
        False,
    )
    return retained


def recall_context(
    bank_id: str,
    agent_name: str,
    principal_name: str,
    category: str,
) -> tuple[list[str], float]:
    """Return relevant memory facts and the call latency in milliseconds."""
    query = (
        f"Loan history and defaults for agent {agent_name}, other agents of "
        f"principal {principal_name}, and category {category}"
    )

    def action() -> list[str]:
        response = _get_client().recall(
            bank_id=bank_id,
            query=query,
            budget="low",
            max_tokens=1200,
            tags=[principal_name, category],
            tags_match="any",
        )
        results = getattr(response, "results", None) or []
        return [str(item.text) for item in results if getattr(item, "text", None)]

    facts, latency_ms = _run("recall_context", action, [])
    return facts, latency_ms


def reflect_beliefs(bank_id: str, question: str) -> str:
    """Ask Hindsight to reflect on the patterns it has learned."""
    text, _ = _run(
        "reflect_beliefs",
        lambda: _get_client().reflect(bank_id=bank_id, query=question).text or "",
        "",
    )
    return text
