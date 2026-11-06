"""Command-line Memory OFF vs Memory ON simulation.

Run from the backend directory:

    python -m scripts.run_sim --rounds 40 --seed 7
    python -m scripts.run_sim --rounds 40 --seed 7 --fake
"""

from __future__ import annotations

import argparse

from app.services import simulator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VouchAI Memory OFF vs ON simulator")
    parser.add_argument("--rounds", type=int, default=40)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use the in-process fake memory/underwriter (no network calls)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = simulator.run_simulation(
        rounds=args.rounds,
        seed=args.seed,
        fake=args.fake,
    )

    print(
        f"VouchAI simulator | mode={result['mode']} seed={result['seed']} "
        f"rounds={result['rounds']} run={result['run_id']}"
    )
    print(
        f"{'RND':>3} {'AGENT':<14} {'CATEGORY':<15} {'AMOUNT':>7}  "
        f"{'OFF':<8} {'LOSS':>6}  {'ON':<8} {'LOSS':>6}  "
        f"{'CUM OFF':>8} {'CUM ON':>8}"
    )

    for off, on in zip(result["off"], result["on"]):
        print(
            f"{off['round']:>3} {off['agent']:<14} {off['category']:<15} "
            f"${off['amount']:>6.0f}  {off['decision']:<8} ${off['loss']:>5.0f}  "
            f"{on['decision']:<8} ${on['loss']:>5.0f}  "
            f"${off['cum_loss']:>7.0f} ${on['cum_loss']:>7.0f}"
        )

    print()
    print(
        f"{'MODE':<5} {'APPROVALS':>9} {'DENIALS':>8} {'TOTAL LOSS':>11} "
        f"{'NET PNL':>10} {'AVG LATENCY':>12}"
    )
    for mode in ("off", "on"):
        summary = result["summary"][mode]
        print(
            f"{mode.upper():<5} {summary['approvals']:>9} {summary['denials']:>8} "
            f"${summary['total_loss']:>10.2f} ${summary['net_pnl']:>9.2f} "
            f"{summary['avg_latency_ms']:>10.1f} ms"
        )

    print()
    print("Ground truth (end-of-demo reveal):")
    for key, value in result["ground_truth"].items():
        print(f"  {key}: {value}")

    path = simulator.save_result(result)
    print()
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
