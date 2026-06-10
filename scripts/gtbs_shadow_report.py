#!/usr/bin/env python3
"""Summarize GTBS shadow divergence — delegates to Phase A divergence analytics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer


def main() -> int:
    parser = argparse.ArgumentParser(description="GTBS shadow divergence report")
    parser.add_argument(
        "--base-dir",
        default="memory",
        help="Memory base dir containing observability/gtbs_shadow.jsonl",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    report = DivergenceAnalyzer(args.base_dir).analyze().to_dict()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"GTBS shadow report — {report.get('source_path')}")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
