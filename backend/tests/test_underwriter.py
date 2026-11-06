"""Offline tests for the LLM underwriter (no network calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import underwriter  # noqa: E402
from app.services.scoring import ScoreBreakdown  # noqa: E402


class FakeGroq:
    """Minimal stand-in for groq.Groq with chat.completions.create."""

    def __init__(self, handler):
        self.handler = handler
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, *, model, messages, temperature):
        self.calls.append(
            {"model": model, "messages": messages, "temperature": temperature}
        )
        content = self.handler(model, len(self.calls))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def formula(limit: float = 600.0) -> ScoreBreakdown:
    return ScoreBreakdown(
        score=75.0,
        confidence=1.0,
        components={},
        formula_limit=limit,
    )


@pytest.fixture(autouse=True)
def groq_models(monkeypatch):
    monkeypatch.setenv("GROQ_MODEL", "primary-model")
    monkeypatch.setenv("GROQ_FALLBACK_MODEL", "fallback-model")


def test_parse_json_with_code_fences() -> None:
    raw = (
        "```json\n"
        '{"multiplier": 0.2, "rationale": "NovaOps defaulted on data-scraping."}\n'
        "```"
    )
    multiplier, rationale = underwriter.parse_multiplier(raw)

    assert multiplier == pytest.approx(0.2)
    assert "NovaOps" in rationale


def test_parse_json_with_nested_braces_in_rationale() -> None:
    raw = 'Here: {"multiplier": 0.4, "rationale": "Saw {odd} defaults."}'
    multiplier, rationale = underwriter.parse_multiplier(raw)

    assert multiplier == pytest.approx(0.4)
    assert rationale == "Saw {odd} defaults."


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [(5, 1.2), (1.2, 1.2), (0, 0.0), (-3, 0.0), (0.75, 0.75)],
)
def test_multiplier_clamping(raw_value: float, expected: float) -> None:
    payload = json.dumps({"multiplier": raw_value, "rationale": "clamped"})
    multiplier, _ = underwriter.parse_multiplier(payload)

    assert multiplier == pytest.approx(expected)


def test_final_limit_math_and_decision(monkeypatch) -> None:
    fake = FakeGroq(
        lambda model, n: '{"multiplier": 0.2, "rationale": "NovaOps defaults."}'
    )
    monkeypatch.setattr(underwriter, "_get_groq_client", lambda: fake)

    result = underwriter.decide(
        agent="scraper-07",
        principal="NovaOps",
        category="data-scraping",
        amount=150.0,
        formula=formula(600.0),
        memory_facts=["NovaOps defaulted on a data-scraping loan."],
        memory_on=True,
    )

    assert result["formula_limit"] == 600.0
    assert result["final_limit"] == pytest.approx(120.0)
    assert result["multiplier"] == pytest.approx(0.2)
    assert result["decision"] == "denied"
    assert result["memory_used"] is True
    assert result["memory_facts"] == ["NovaOps defaulted on a data-scraping loan."]


def test_memory_off_uses_formula_only(monkeypatch) -> None:
    def explode():
        raise AssertionError("Groq must not be called when memory is off")

    monkeypatch.setattr(underwriter, "_get_groq_client", explode)

    result = underwriter.decide(
        agent="scraper-07",
        principal="NovaOps",
        category="data-scraping",
        amount=150.0,
        formula=formula(600.0),
        memory_facts=["ignored"],
        memory_on=False,
    )

    assert result["multiplier"] == 1.0
    assert result["final_limit"] == 600.0
    assert result["decision"] == "approved"
    assert result["rationale"] == "Formula only (memory off)."
    assert result["memory_used"] is False
    assert result["memory_facts"] == []


def test_fallback_model_after_primary_failure(monkeypatch) -> None:
    def handler(model: str, _n: int) -> str:
        if model == "primary-model":
            return "this is not JSON"
        return '{"multiplier": 0.5, "rationale": "Fallback model read memory."}'

    fake = FakeGroq(handler)
    monkeypatch.setattr(underwriter, "_get_groq_client", lambda: fake)

    result = underwriter.decide(
        agent="scraper-07",
        principal="NovaOps",
        category="data-scraping",
        amount=100.0,
        formula=formula(600.0),
        memory_facts=["NovaOps defaulted."],
        memory_on=True,
    )

    assert [call["model"] for call in fake.calls] == [
        "primary-model",
        "fallback-model",
    ]
    assert result["multiplier"] == pytest.approx(0.5)
    assert result["final_limit"] == pytest.approx(300.0)
    assert result["decision"] == "approved"
    assert result["model"] == "fallback-model"


def test_total_failure_falls_back_to_formula(monkeypatch) -> None:
    def handler(_model: str, _n: int) -> str:
        raise RuntimeError("model unavailable")

    fake = FakeGroq(handler)
    monkeypatch.setattr(underwriter, "_get_groq_client", lambda: fake)

    result = underwriter.decide(
        agent="scraper-07",
        principal="NovaOps",
        category="data-scraping",
        amount=100.0,
        formula=formula(600.0),
        memory_facts=["NovaOps defaulted."],
        memory_on=True,
    )

    assert len(fake.calls) == 2
    assert result["multiplier"] == 1.0
    assert result["final_limit"] == 600.0
    assert result["decision"] == "approved"
    assert result["rationale"] == "Fallback: model unavailable"
    assert result["memory_used"] is True


def test_prompt_uses_temperature_and_memory_only(monkeypatch) -> None:
    fake = FakeGroq(
        lambda model, n: '{"multiplier": 1.0, "rationale": "No relevant memory."}'
    )
    monkeypatch.setattr(underwriter, "_get_groq_client", lambda: fake)

    underwriter.decide(
        agent="scraper-07",
        principal="NovaOps",
        category="data-scraping",
        amount=100.0,
        formula=formula(600.0),
        memory_facts=["NovaOps defaulted once."],
        memory_on=True,
    )

    call = fake.calls[0]
    assert call["temperature"] == pytest.approx(0.1)
    assert call["messages"][0]["role"] == "system"
    assert "MEMORY facts" in call["messages"][1]["content"]
    assert "NovaOps defaulted once." in call["messages"][1]["content"]
