#!/usr/bin/env python3
"""
GTBS-L2 Semantic Alignment Report — machine metrics → human continuity narrative.

Read-only. Zero runtime mutation. Zero governance authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.governance.l2.loader import load_snapshot_from_base_dir, load_temporal_window
from core.governance.l2.render import GTBSL2Renderer


def main(
    base_dir: str,
    *,
    as_json: bool = False,
    temporal: bool = False,
    fusion: bool = False,
    attractor: bool = False,
    window_days: int = 7,
) -> int:
    renderer = GTBSL2Renderer()

    if attractor:
        report = renderer.render_attractor(base_dir, window_days=window_days)
        if as_json:
            payload = {**report.to_dict(), "base_dir": str(Path(base_dir).resolve())}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(renderer.render_attractor_text(base_dir, window_days=window_days))
        return 0

    if fusion:
        report = renderer.render_fusion(base_dir, window_days=window_days)
        if as_json:
            payload = {**report.to_dict(), "base_dir": str(Path(base_dir).resolve())}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(renderer.render_fusion_text(base_dir, window_days=window_days))
        return 0

    if temporal:
        window = load_temporal_window(base_dir, window_days=window_days)
        report = renderer.render_temporal(window)
        if as_json:
            payload = {**report.to_dict(), "base_dir": str(Path(base_dir).resolve())}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(renderer.render_temporal_text(window))
        return 0

    snapshot = load_snapshot_from_base_dir(base_dir)
    result = renderer.render(snapshot)

    if as_json:
        payload = {**result, "base_dir": str(Path(base_dir).resolve())}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(renderer.render_narrative_text(snapshot))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GTBS-L2 semantic alignment report (read-only)")
    parser.add_argument("--base-dir", required=True, help="BM memory base directory")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    parser.add_argument(
        "--temporal",
        action="store_true",
        help="Emit L2 v0.2 temporal continuity report",
    )
    parser.add_argument(
        "--fusion",
        action="store_true",
        help="Emit L2 v0.3 cross-stream fusion report",
    )
    parser.add_argument(
        "--attractor",
        action="store_true",
        help="Emit L2 v0.5 latent attractor inference report",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="Window size in days for --temporal / --fusion / --attractor (default: 7)",
    )
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.base_dir,
            as_json=args.json,
            temporal=args.temporal,
            fusion=args.fusion,
            attractor=args.attractor,
            window_days=args.window_days,
        )
    )
