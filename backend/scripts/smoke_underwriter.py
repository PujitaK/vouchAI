"""Manual smoke test for the Hindsight + Groq underwriting path.

This makes real network calls to Hindsight and Groq. Run it only when the
backend/.env values are configured:

    python -m scripts.smoke_underwriter
"""

from __future__ import annotations

from app.services import memory, underwriter
from app.services.scoring import LoanSample, TaskSample, compute_score

BANK_ID = "vouchai-smoke-uw"
PRINCIPAL = "NovaOps"
CATEGORY = "data-scraping"
AGENT = "scraper-07"
AMOUNT = 400.0


def main() -> None:
    memory.ensure_bank(BANK_ID)

    for round_no, agent_name in enumerate(
        ("scraper-07", "scraper-11", "scraper-02", "scraper-04"),
        start=1,
    ):
        memory.retain_outcome(
            BANK_ID,
            agent_name,
            PRINCIPAL,
            CATEGORY,
            AMOUNT,
            "defaulted",
            round_no=round_no,
        )

    facts, recall_latency_ms = memory.recall_context(
        BANK_ID, AGENT, PRINCIPAL, CATEGORY
    )

    # A healthy formula baseline so the memory effect is easy to see.
    formula = compute_score(
        [TaskSample(True, 100.0) for _ in range(20)],
        [LoanSample("repaid")],
    )

    with_memory = underwriter.decide(
        AGENT, PRINCIPAL, CATEGORY, AMOUNT, formula, facts, True
    )
    without_memory = underwriter.decide(
        AGENT, PRINCIPAL, CATEGORY, AMOUNT, formula, facts, False
    )

    print(f"Bank: {BANK_ID}")
    print(f"Formula limit: {formula.formula_limit:.2f}")
    print(f"Recall: {len(facts)} facts in {recall_latency_ms:.0f} ms")
    for fact in facts:
        print(f"  - {fact}")
    print()
    print(f"{'MODE':<6} {'MULT':>6} {'FINAL':>8}  RATIONALE")
    for label, result in (("ON", with_memory), ("OFF", without_memory)):
        print(
            f"{label:<6} {result['multiplier']:>6.2f} "
            f"{result['final_limit']:>8.2f}  {result['rationale']}"
        )


if __name__ == "__main__":
    main()
