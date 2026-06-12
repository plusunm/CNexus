#!/usr/bin/env python3
"""CNexus L8/G8 Influence Causality Test Suite CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.tests.influence.runner import InfluenceTestRunner


def main() -> int:
    parser = argparse.ArgumentParser(description="L8/G8 influence causality test (observational only)")
    parser.add_argument(
        "--mode",
        choices=("full", "baseline", "injection"),
        default="full",
        help="Run mode",
    )
    parser.add_argument("--json-out", help="Write final report JSON")
    parser.add_argument("--text", action="store_true", help="Human-readable summary")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    runner = InfluenceTestRunner(root)

    default_out = root / "docs" / "semantic_safety" / "l8g8_influence_report.json"
    json_out = Path(args.json_out) if args.json_out else default_out

    if args.mode == "baseline":
        payload = runner.run_baseline()
    elif args.mode == "injection":
        payload = runner.run_injection()
    else:
        payload = runner.run_full(json_out=json_out)

    if args.mode == "full" and not args.json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)

    if args.text or args.mode != "full":
        if args.mode == "full":
            print(_render_summary(payload))
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif args.mode == "full":
        print(_render_summary(payload))
        print(f"\nReport written: {json_out}")
    return 0


def _render_summary(report: dict) -> str:
    result = report.get("result", {})
    conclusion = report.get("conclusion", {})
    lines = [
        "=== L8/G8 Influence Causality Test v1 ===",
        f"Response drift: {result.get('response_drift', 'n/a')}",
        f"Memory drift:   {result.get('memory_drift', 'n/a')}",
        f"Routing drift:  {result.get('routing_drift', 'n/a')}",
        f"Semantic leakage: {conclusion.get('semantic_leakage')}",
        f"Control leakage:  {conclusion.get('control_leakage')}",
        f"Interpretation:   {', '.join(report.get('interpretation', []))}",
        "",
        "(observational-only — no runtime mutation)",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
