"""Preload simulated loan outcomes into Hindsight memory.

Run from the backend directory:

    python -m scripts.preload_memory
    python -m scripts.preload_memory --bank vouchai-lender-main --max 40
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.services import memory

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHED_RUN_PATH = PROJECT_ROOT / "data" / "cached_run.json"
DEFAULT_BANK_ID = "vouchai-lender-main"
VALID_OUTCOMES = {"repaid", "defaulted"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preload simulated loan outcomes into Hindsight memory"
    )
    parser.add_argument("--bank", default=DEFAULT_BANK_ID)
    parser.add_argument("--max", dest="max_rows", type=int, default=40)
    return parser.parse_args()


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Cached run not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Cached run is not valid JSON: {exc}") from exc

    rows = payload.get("on")
    if not isinstance(rows, list):
        raise SystemExit("Cached run has no 'on' list")
    return [row for row in rows if isinstance(row, dict)]


def _normalize_row(row: dict[str, Any]) -> dict[str, Any] | None:
    agent = str(row.get("agent", "")).strip()
    principal = str(row.get("principal", "")).strip()
    category = str(row.get("category", "")).strip()
    outcome = str(row.get("outcome", "")).strip().lower()

    if not agent or not principal or not category:
        return None
    if outcome not in VALID_OUTCOMES:
        return None

    try:
        amount = float(row.get("amount", 0))
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None

    round_no = row.get("round")
    if isinstance(round_no, (int, float)):
        round_no = int(round_no)
    else:
        round_no = None

    return {
        "agent": agent,
        "principal": principal,
        "category": category,
        "amount": amount,
        "outcome": outcome,
        "round": round_no,
    }


def main() -> None:
    args = _parse_args()
    if args.max_rows < 0:
        raise SystemExit("--max must be greater than or equal to 0")

    rows = [
        normalized
        for row in _load_rows(CACHED_RUN_PATH)
        if (normalized := _normalize_row(row)) is not None
    ]
    rows = rows[: args.max_rows]

    if not rows:
        print("No resolved ON-mode outcomes found; nothing to preload.")
        return

    print(f"Preloading {len(rows)} outcomes into bank '{args.bank}'...")
    print("Note: preloading is append-only; re-running may duplicate memories.")

    memory.ensure_bank(args.bank)

    loaded = 0
    failed = 0
    for index, row in enumerate(rows, start=1):
        ok = memory.retain_outcome(
            bank_id=args.bank,
            agent_name=row["agent"],
            principal_name=row["principal"],
            category=row["category"],
            amount=row["amount"],
            outcome=row["outcome"],
            round_no=row["round"],
        )
        if ok:
            loaded += 1
            status = "ok"
        else:
            failed += 1
            status = "failed"
        print(
            f"[{index}/{len(rows)}] {status}: {row['agent']} "
            f"({row['principal']}) ${row['amount']:.0f} {row['outcome']}"
        )

    print(f"Done. Loaded {loaded}/{len(rows)} outcomes into '{args.bank}'.")
    if failed:
        print(f"{failed} retain call(s) failed; see warnings above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
