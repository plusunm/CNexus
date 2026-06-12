#!/usr/bin/env python3
"""Verify Observation Gateway contract compliance (P1 smoke check)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.observation import OBSERVATION_NORTH_STAR, ObservationGateway
from core.observation.schema import CONTRACT_META


def main() -> int:
    parser = argparse.ArgumentParser(description="Observation Gateway contract check")
    parser.add_argument("--base-dir", required=True, help="BM_MEMORY_DIR")
    parser.add_argument("--json-out", help="Write check result JSON")
    args = parser.parse_args()

    gw = ObservationGateway(args.base_dir)
    sample = gw.ingest(
        source="observation_gateway_check",
        event_type="contract_smoke",
        payload={"check": "north_star_ack", "laws": list(OBSERVATION_NORTH_STAR)},
    )

    result = {
        "contract_version": CONTRACT_META.get("contract_version", "0.1.0"),
        "north_star": list(OBSERVATION_NORTH_STAR),
        "contract_meta": CONTRACT_META,
        "sample_event": sample,
        "stream": str(gw.stream_path),
        "append_only": True,
    }

    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
