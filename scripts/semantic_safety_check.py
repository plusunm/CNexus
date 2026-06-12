#!/usr/bin/env python3
"""
CNexus Semantic Safety Stack v2 — CI checker.

Scans observational stack for deprecated agency terms and control-leakage output shapes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.governance.semantic_safety.rename_map import CDG_CONTROL_EXEMPT, RENAME_MAP

SCAN_ROOTS = [
    ROOT / "core" / "governance" / "l2",
    ROOT / "core" / "governance" / "l3",
    ROOT / "core" / "governance" / "ecology",
    ROOT / "core" / "governance" / "singularity",
    ROOT / "core" / "governance" / "gtbs",
    ROOT / "core" / "governance" / "continuity",
    ROOT / "core" / "governance" / "semantic_safety",
]

CDG_ROOT = ROOT / "core" / "governance" / "cdg"

DEPRECATED_CLASS_PATTERN = re.compile(
    r"^class\s+(" + "|".join(re.escape(n) for n in RENAME_MAP) + r")\b",
    re.MULTILINE,
)

CONTROL_LEAKAGE_KEYS = (
    '"collapse_detected"',
    '"arbitration_result"',
    '"system_responses"',
    '"winner":',
    '"recommended_action"',
)

REQUIRED_ENVELOPE_KEYS = ("role", "non_actionable", "observational_safe")


def _scan_files() -> list[Path]:
    files: list[Path] = []
    for base in SCAN_ROOTS:
        if base.exists():
            files.extend(base.rglob("*.py"))
    return sorted(set(files))


def check_deprecated_class_definitions(files: list[Path]) -> list[dict]:
    violations = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for match in DEPRECATED_CLASS_PATTERN.finditer(text):
            name = match.group(1)
            if name in CDG_CONTROL_EXEMPT:
                continue
            line = text.count("\n", 0, match.start()) + 1
            violations.append(
                {
                    "type": "deprecated_class_definition",
                    "file": str(path.relative_to(ROOT)),
                    "line": line,
                    "symbol": name,
                    "expected": RENAME_MAP[name],
                }
            )
    return violations


def check_control_leakage_in_reports(files: list[Path]) -> list[dict]:
    violations = []
    report_files = [p for p in files if "report" in p.name.lower() or p.name.endswith("_report.py")]
    for path in report_files:
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ROOT))
        for key in CONTROL_LEAKAGE_KEYS:
            if key in text and "deprecated" not in text[max(0, text.find(key) - 80) : text.find(key)]:
                violations.append(
                    {
                        "type": "control_leakage_key",
                        "file": rel,
                        "pattern": key,
                    }
                )
    return violations


def run_runtime_baseline() -> dict:
    from core.governance.l3 import build_l3_g1_report, build_l3_g6_report, build_l3_g7_report

    g1 = build_l3_g1_report(use_l2_coupling=False).to_dict()
    g6 = build_l3_g6_report(use_l2_coupling=False).to_dict()
    g7 = build_l3_g7_report(use_l2_coupling=False).to_dict()

    missing = []
    for label, payload in (("L3-G1", g1), ("L3-G6", g6), ("L3-G7", g7)):
        for key in REQUIRED_ENVELOPE_KEYS:
            if key not in payload:
                missing.append({"report": label, "missing_key": key})

    return {
        "reports_checked": ["L3-G1", "L3-G6", "L3-G7"],
        "envelope_gaps": missing,
        "samples": {
            "g1_has_simulation_result": "simulation_result" in g1,
            "g6_has_severity_band": "collapse_severity_band" in g6,
            "g6_has_retention_metric": "explainability_retention_metric" in g6,
        },
    }


def run_v3_attack_simulation() -> dict:
    from core.governance.semantic_safety.v3 import build_semantic_safety_v3_report

    report = build_semantic_safety_v3_report()
    payload = report.to_dict()
    return {
        "semantic_safety_v3": payload.get("semantic_safety_v3"),
        "attack_surface_level": payload.get("attack_surface_map", {}).get("level"),
        "misinterpretation_risk": payload.get("attack_score", {}).get("misinterpretation_risk"),
        "collapse_point": payload.get("control_inference_chain", {}).get("collapse_point"),
        "mitigation_tag_count": len(payload.get("mitigation_tags", [])),
    }


def build_audit_report(*, strict: bool, include_v3: bool = False) -> dict:
    files = _scan_files()
    deprecated = check_deprecated_class_definitions(files)
    leakage = check_control_leakage_in_reports(files)
    baseline = run_runtime_baseline()

    status = "pass"
    if deprecated or baseline["envelope_gaps"]:
        status = "fail" if strict else "warn"
    if leakage and status == "pass":
        status = "warn"

    result = {
        "semantic_safety_version": "2.0.0",
        "status": status,
        "deprecated_class_definitions": deprecated,
        "control_leakage_patterns": leakage,
        "runtime_baseline": baseline,
        "rename_map": RENAME_MAP,
    }
    if include_v3:
        result["v3_attack_simulation"] = run_v3_attack_simulation()
        result["semantic_safety_version"] = "3.0.0"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="CNexus Semantic Safety checker (v2 + optional v3)")
    parser.add_argument("--strict", action="store_true", help="Fail on any deprecated class definition")
    parser.add_argument("--v3", action="store_true", help="Include v3 attack simulation summary")
    parser.add_argument("--json-out", help="Write audit JSON to path")
    args = parser.parse_args()

    report = build_audit_report(strict=args.strict, include_v3=args.v3)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if report["status"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
