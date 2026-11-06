"""Offline tests for the Hindsight memory wrapper (no network calls)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import memory  # noqa: E402


class FakeHindsight:
    def __init__(self, recall_handler=None):
        self.calls: list[tuple[str, dict]] = []
        self.closed = False
        self._recall_handler = recall_handler or (
            lambda kwargs: SimpleNamespace(
                results=[SimpleNamespace(text="fact one"), SimpleNamespace(text="fact two")]
            )
        )

    def create_bank(self, **kwargs):
        self.calls.append(("create_bank", kwargs))
        return object()

    def retain(self, **kwargs):
        self.calls.append(("retain", kwargs))
        return object()

    def recall(self, **kwargs):
        self.calls.append(("recall", kwargs))
        return self._recall_handler(kwargs)

    def reflect(self, **kwargs):
        self.calls.append(("reflect", kwargs))
        return SimpleNamespace(text="NovaOps defaults on data-scraping.")

    def close(self):
        self.closed = True


@pytest.fixture
def fake_client(monkeypatch):
    fake = FakeHindsight()
    monkeypatch.setattr(memory, "_get_client", lambda: fake)
    return fake


def test_ensure_bank_uses_mission(fake_client) -> None:
    assert memory.ensure_bank("vouchai-test") is True

    name, kwargs = fake_client.calls[0]
    assert name == "create_bank"
    assert kwargs["bank_id"] == "vouchai-test"
    assert kwargs["mission"] == memory.MISSION


def test_retain_outcome_content_and_context(fake_client) -> None:
    assert (
        memory.retain_outcome(
            "bank",
            agent_name="scraper-07",
            principal_name="NovaOps",
            category="data-scraping",
            amount=400,
            outcome="defaulted",
        )
        is True
    )

    _, kwargs = fake_client.calls[0]
    assert "scraper-07" in kwargs["content"]
    assert "NovaOps" in kwargs["content"]
    assert "data-scraping" in kwargs["content"]
    assert "DEFAULTED" in kwargs["content"]
    assert kwargs["context"] == "loan outcome"
    assert kwargs["retain_async"] is False


def test_retain_outcome_repaid_wording(fake_client) -> None:
    memory.retain_outcome(
        "bank", "scraper-07", "NovaOps", "data-scraping", 400, "repaid"
    )

    _, kwargs = fake_client.calls[0]
    assert "REPAID in full" in kwargs["content"]


def test_retain_decision_content_and_context(fake_client) -> None:
    memory.retain_decision(
        "bank",
        "scraper-07",
        "NovaOps",
        "data-scraping",
        400,
        "denied",
        "Memory shows prior defaults.",
    )

    _, kwargs = fake_client.calls[0]
    assert "DENIED" in kwargs["content"]
    assert "Memory shows prior defaults" in kwargs["content"]
    assert kwargs["context"] == "underwriting decision"


def test_recall_context_returns_texts_and_latency(fake_client) -> None:
    facts, latency_ms = memory.recall_context(
        "bank", "scraper-07", "NovaOps", "data-scraping"
    )

    assert facts == ["fact one", "fact two"]
    assert latency_ms >= 0.0

    _, kwargs = fake_client.calls[0]
    assert kwargs["budget"] == "low"
    assert kwargs["max_tokens"] == 1200
    assert "scraper-07" in kwargs["query"]
    assert "NovaOps" in kwargs["query"]
    assert "data-scraping" in kwargs["query"]


def test_recall_context_retries_once(monkeypatch) -> None:
    attempts = {"count": 0}

    def handler(_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("transient")
        return SimpleNamespace(results=[SimpleNamespace(text="second try")])

    fake = FakeHindsight(recall_handler=handler)
    monkeypatch.setattr(memory, "_get_client", lambda: fake)

    facts, _ = memory.recall_context("bank", "a", "p", "c")

    assert facts == ["second try"]
    assert attempts["count"] == 2
    assert len(fake.calls) == 2


def test_recall_context_fails_safe(monkeypatch, caplog) -> None:
    def handler(_kwargs):
        raise RuntimeError("down")

    fake = FakeHindsight(recall_handler=handler)
    monkeypatch.setattr(memory, "_get_client", lambda: fake)

    with caplog.at_level(logging.WARNING):
        facts, latency_ms = memory.recall_context("bank", "a", "p", "c")

    assert facts == []
    assert latency_ms >= 0.0
    assert len(fake.calls) == 2
    assert "recall_context" in caplog.text
    assert "ms" in caplog.text


def test_reflect_beliefs(fake_client) -> None:
    text = memory.reflect_beliefs("bank", "What defaults?")
    assert text == "NovaOps defaults on data-scraping."

    _, kwargs = fake_client.calls[0]
    assert kwargs["query"] == "What defaults?"


def test_reflect_beliefs_fails_safe(monkeypatch) -> None:
    class Broken(FakeHindsight):
        def reflect(self, **kwargs):
            raise RuntimeError("down")

    monkeypatch.setattr(memory, "_get_client", lambda: Broken())

    assert memory.reflect_beliefs("bank", "question") == ""
