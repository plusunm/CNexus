#!/usr/bin/env python3
"""
L3 Boundary Probe Report — G0–G7 governance observation stack.

S13–S20 + G4 reflexivity constraints: zero runtime control; observational only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.l3 import (
    build_l3_g0_report,
    build_l3_g1_report,
    build_l3_g2_report,
    build_l3_g3_report,
    build_l3_g4_report,
    build_l3_g5_report,
    build_l3_g6_report,
    build_l3_g7_report,
)


def main(
    *,
    as_json: bool = False,
    base_dir: str | None = None,
    window_days: int = 7,
    synthetic: bool = False,
    g1: bool = False,
    g2: bool = False,
    g3: bool = False,
    g4: bool = False,
    g5: bool = False,
    g6: bool = False,
    g7: bool = False,
) -> int:
    if g7:
        report = build_l3_g7_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g6:
        report = build_l3_g6_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g5:
        report = build_l3_g5_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g4:
        report = build_l3_g4_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g3:
        report = build_l3_g3_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g2:
        report = build_l3_g2_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    if g1:
        report = build_l3_g1_report(
            base_dir=None if synthetic else base_dir,
            window_days=window_days,
            use_l2_coupling=not synthetic and base_dir is not None,
        )
        if as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(report.render_text())
        return 0

    report = build_l3_g0_report(
        base_dir if not synthetic else None,
        window_days=window_days,
        use_l2_coupling=not synthetic and base_dir is not None,
    )
    if as_json:
        print(json.dumps(report.render(), indent=2, ensure_ascii=False))
    else:
        print(report.render_text())
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="L3 boundary probe (G0–G7, read-only)")
    parser.add_argument("--base-dir", help="BM memory dir for L2→L3 coupling harness")
    parser.add_argument("--window-days", type=int, default=7, help="Window for L2 stack (default: 7)")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic signals only (no L2 coupling)",
    )
    parser.add_argument("--g1", action="store_true", help="L3-G1 constraint graph report")
    parser.add_argument("--g2", action="store_true", help="L3-G2 execution shadow report")
    parser.add_argument("--g3", action="store_true", help="L3-G3 power field optimization report")
    parser.add_argument("--g4", action="store_true", help="L3-G4 meta-governance reflection report")
    parser.add_argument("--g5", action="store_true", help="L3-G5 meta-meta governance boundary report")
    parser.add_argument("--g6", action="store_true", help="L3-G6 collapse stability / explainability report")
    parser.add_argument("--g7", action="store_true", help="L3-G7 layerless kernel (field-native) report")
    args = parser.parse_args()
    raise SystemExit(
        main(
            as_json=args.json,
            base_dir=args.base_dir,
            window_days=args.window_days,
            synthetic=args.synthetic,
            g1=args.g1,
            g2=args.g2,
            g3=args.g3,
            g4=args.g4,
            g5=args.g5,
            g6=args.g6,
            g7=args.g7,
        )
    )
