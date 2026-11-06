"""LLM-assisted underwriting on top of the formula limit.

Memory facts are the only evidence the model may use. Any model or parsing
failure falls back to the formula (multiplier 1.0), never to a hidden default.
"""

from __future__ import annotations

import atexit
import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_FALLBACK_MODEL = "openai/gpt-oss-20b"
MIN_MULTIPLIER = 0.0
MAX_MULTIPLIER = 1.2

SYSTEM_PROMPT = (
    "You are a cautious lending underwriter for autonomous AI agents. "
    "Use ONLY the MEMORY facts given; do not invent history. "
    "If memory is empty or irrelevant, return multiplier 1.0. "
    "Lower the multiplier sharply (0.0-0.3) when memory shows defaults by the "
    "same principal on the same category. A clean repayment history for the "
    "same agent may raise the multiplier up to 1.2. "
    'Reply with ONLY a JSON object: '
    '{"multiplier": number 0-1.2, "rationale": "max 2 sentences citing specific memory facts"}'
)

_groq_client: Any | None = None


class Formula(Protocol):
    formula_limit: float


def _primary_model() -> str:
    return os.getenv("GROQ_MODEL") or DEFAULT_MODEL


def _fallback_model() -> str:
    return os.getenv("GROQ_FALLBACK_MODEL") or DEFAULT_FALLBACK_MODEL


def _get_groq_client() -> Any:
    """Lazily create and reuse one Groq client."""
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Groq credentials are not configured")
        _groq_client = Groq(api_key=api_key)
        atexit.register(_close_groq_client)
    return _groq_client


def _close_groq_client() -> None:
    global _groq_client
    if _groq_client is not None:
        close = getattr(_groq_client, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:  # pragma: no cover - shutdown best effort
                logger.warning("Groq client close failed (%s)", type(exc).__name__)
        _groq_client = None


def _extract_json_object(text: str) -> str:
    """Return the first balanced {...} block, ignoring braces inside strings."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("unterminated JSON object")


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped[3:]
        if stripped.startswith(("json", "JSON")):
            stripped = stripped[4:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def clamp_multiplier(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("multiplier is not finite")
    return max(MIN_MULTIPLIER, min(MAX_MULTIPLIER, value))


def parse_multiplier(raw: str) -> tuple[float, str]:
    """Parse the model reply into a clamped multiplier and rationale."""
    payload = json.loads(_extract_json_object(_strip_code_fences(raw)))
    multiplier = clamp_multiplier(float(payload["multiplier"]))
    rationale = str(payload.get("rationale", "")).strip()
    return multiplier, rationale


def _build_user_prompt(
    agent: str,
    principal: str,
    category: str,
    amount: float,
    formula: Formula,
    memory_facts: list[str],
) -> str:
    facts_block = "\n".join(f"- {fact}" for fact in memory_facts) or "- (no memory facts)"
    return (
        f"Agent: {agent}\n"
        f"Principal: {principal}\n"
        f"Category: {category}\n"
        f"Requested amount: ${amount:.2f}\n"
        f"Formula limit: ${formula.formula_limit:.2f}\n\n"
        f"MEMORY facts:\n{facts_block}\n\n"
        "Return only the JSON object."
    )


def _chat(model: str, user_prompt: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def _result(
    multiplier: float,
    formula: Formula,
    amount: float,
    rationale: str,
    memory_used: bool,
    memory_facts: list[str],
    model: str | None,
    latency_ms: float,
) -> dict[str, Any]:
    final_limit = round(formula.formula_limit * multiplier, 2)
    decision = "approved" if amount <= final_limit and final_limit > 0 else "denied"
    return {
        "multiplier": round(multiplier, 4),
        "formula_limit": formula.formula_limit,
        "final_limit": final_limit,
        "decision": decision,
        "rationale": rationale,
        "memory_used": memory_used,
        "memory_facts": list(memory_facts),
        "model": model,
        "llm_latency_ms": round(latency_ms, 1),
    }


def decide(
    agent: str,
    principal: str,
    category: str,
    amount: float,
    formula: Formula,
    memory_facts: list[str],
    memory_on: bool,
) -> dict[str, Any]:
    """Return a multiplier-adjusted decision, citing memory when enabled."""
    facts = [str(fact) for fact in (memory_facts or [])]

    if not memory_on:
        return _result(
            1.0,
            formula,
            amount,
            "Formula only (memory off).",
            False,
            [],
            None,
            0.0,
        )

    user_prompt = _build_user_prompt(agent, principal, category, amount, formula, facts)
    started = time.perf_counter()

    for model in (_primary_model(), _fallback_model()):
        try:
            content = _chat(model, user_prompt)
            multiplier, rationale = parse_multiplier(content)
            latency_ms = (time.perf_counter() - started) * 1000.0
            return _result(
                multiplier,
                formula,
                amount,
                rationale or "Memory-adjusted underwriting.",
                True,
                facts,
                model,
                latency_ms,
            )
        except Exception as exc:
            logger.warning(
                "Groq underwriting attempt failed with %s (%s)",
                model,
                type(exc).__name__,
            )

    latency_ms = (time.perf_counter() - started) * 1000.0
    return _result(
        1.0,
        formula,
        amount,
        "Fallback: model unavailable",
        True,
        facts,
        None,
        latency_ms,
    )
