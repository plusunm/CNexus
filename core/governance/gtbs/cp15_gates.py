"""CP-1.5 acceptance gates G1–G5 (engineering verification)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from core.governance.gtbs.write_intent import WriteIntentKind

ROOT = Path(__file__).resolve().parents[3]

KIND_ADAPTER_FILES: Dict[WriteIntentKind, str] = {
    WriteIntentKind.CAPTURE: "capture_adapter.py",
    WriteIntentKind.RECALL_SIDE_EFFECT: "recall_adapter.py",
    WriteIntentKind.CDG_APPLY: "cdg_adapter.py",
    WriteIntentKind.IR_COMMIT: "ir_adapter.py",
    WriteIntentKind.CHAT_DEFERRED: "chat_deferred_adapter.py",
    WriteIntentKind.WORKING_SELF: "working_self_adapter.py",
    WriteIntentKind.GOVERNANCE_CYCLE: "governance_adapter.py",
}

KIND_CALL_HINTS: Dict[WriteIntentKind, List[str]] = {
    WriteIntentKind.CAPTURE: ["maybe_emit_capture", "build_capture_write_intent"],
    WriteIntentKind.RECALL_SIDE_EFFECT: ["maybe_emit_recall"],
    WriteIntentKind.CDG_APPLY: ["maybe_emit_cdg_apply"],
    WriteIntentKind.IR_COMMIT: ["maybe_emit_ir_commit"],
    WriteIntentKind.CHAT_DEFERRED: ["maybe_emit_chat_deferred"],
    WriteIntentKind.WORKING_SELF: ["maybe_emit_working_self"],
    WriteIntentKind.GOVERNANCE_CYCLE: ["maybe_emit_governance_cycle"],
}

API_BYPASS_FILES = [
    ROOT / "api" / "server.py",
    ROOT / "api" / "v1_endpoints.py",
    ROOT / "core" / "openai_compat" / "handler.py",
]

API_BYPASS_PATTERNS = [
    re.compile(r"get_runtime\(\)\.process_interaction\s*\("),
    re.compile(r"get_runtime\(\)\.run_governance_cycle\s*\("),
    re.compile(r"get_runtime\(\)\.recall\s*\("),
    re.compile(r"runtime\.capture\s*\("),
    re.compile(r"runtime\.recall\s*\("),
    re.compile(r"runtime\.run_governance_cycle\s*\("),
]


@dataclass
class GateResult:
    gate_id: str
    passed: bool
    detail: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CP15GateReport:
    results: List[GateResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "gates": [
                {"id": r.gate_id, "passed": r.passed, "detail": r.detail, "data": r.data}
                for r in self.results
            ],
        }


def _adapter_wiring_ok() -> GateResult:
    adapters_dir = ROOT / "core" / "governance" / "gtbs" / "adapters"
    runtime_src = (ROOT / "brain_memory" / "runtime.py").read_text(encoding="utf-8")
    recall_src = (ROOT / "runtime" / "recall_pipeline.py").read_text(encoding="utf-8")
    ir_src = (ROOT / "ir_kernel" / "adapters" / "runtime_facade.py").read_text(encoding="utf-8")
    combined = runtime_src + recall_src + ir_src
    missing: List[str] = []
    for kind, adapter_file in KIND_ADAPTER_FILES.items():
        adapter_path = adapters_dir / adapter_file
        hints = KIND_CALL_HINTS.get(kind, [])
        call_hit = any(h in combined for h in hints)
        if not (adapter_path.exists() and call_hit):
            missing.append(kind.value)
    return GateResult(
        gate_id="G1",
        passed=not missing,
        detail="all WriteIntentKind adapters wired" if not missing else f"missing wiring: {missing}",
        data={"kinds_required": [k.value for k in WriteIntentKind], "missing": missing},
    )


def _analyze_log(path: Path) -> GateResult:
    if not path.exists():
        return GateResult(
            gate_id="G1-runtime",
            passed=True,
            detail="no gtbs_transactions.jsonl yet (static wiring check only)",
            data={"log_path": str(path), "events": 0},
        )
    rows: List[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    kinds_seen: Set[str] = set()
    lineage_ok = 0
    proposals = 0
    commits = 0
    for row in rows:
        if row.get("event_type") == "proposal":
            proposals += 1
            payload = row.get("payload") or {}
            kind = payload.get("write_intent_kind")
            if kind:
                kinds_seen.add(kind)
            prov = payload.get("provenance") or {}
            if prov.get("trace_id") or prov.get("runtime_token"):
                lineage_ok += 1
        if row.get("event_type") == "commit":
            commits += 1
    return GateResult(
        gate_id="G1-runtime",
        passed=True,
        detail=f"log events={len(rows)} kinds={sorted(kinds_seen)}",
        data={
            "log_path": str(path),
            "events": len(rows),
            "proposals": proposals,
            "commits": commits,
            "kinds_seen": sorted(kinds_seen),
            "lineage_on_proposals": lineage_ok,
        },
    )


def _gate_g2_from_log(path: Path) -> GateResult:
    if not path.exists():
        return GateResult(
            gate_id="G2",
            passed=True,
            detail="skipped — no transaction log",
            data={},
        )
    rows: List[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    proposals = [r for r in rows if r.get("event_type") == "proposal"]
    if not proposals:
        return GateResult(gate_id="G2", passed=True, detail="no proposals to check", data={})
    missing_lineage = 0
    for row in proposals:
        prov = (row.get("payload") or {}).get("provenance") or {}
        if not (prov.get("trace_id") or prov.get("runtime_token")):
            missing_lineage += 1
    passed = missing_lineage == 0
    return GateResult(
        gate_id="G2",
        passed=passed,
        detail="all proposals have lineage" if passed else f"{missing_lineage} proposals missing lineage",
        data={"proposals": len(proposals), "missing_lineage": missing_lineage},
    )


def _gate_g3_g4() -> List[GateResult]:
    g3_ok = True
    g3_hits: List[str] = []
    g4_ok = True
    for path in API_BYPASS_FILES:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        if "get_legacy_adapter" not in source and path.name in ("server.py", "v1_endpoints.py"):
            g4_ok = False
        for pattern in API_BYPASS_PATTERNS:
            match = pattern.search(source)
            if not match:
                continue
            if path.name == "handler.py" and "legacy_adapter is not None" in source:
                if pattern.pattern.startswith("runtime\\.process_interaction"):
                    continue
            g3_ok = False
            g3_hits.append(f"{path.name}:{match.group(0)}")
    return [
        GateResult(
            gate_id="G3",
            passed=g3_ok,
            detail="no API write bypass" if g3_ok else f"bypass hits: {g3_hits}",
            data={"hits": g3_hits},
        ),
        GateResult(
            gate_id="G4",
            passed=g4_ok,
            detail="legacy adapter present in API entrypoints" if g4_ok else "missing get_legacy_adapter",
            data={},
        ),
    ]


def _gate_g5(path: Path) -> GateResult:
    if not path.exists():
        return GateResult(
            gate_id="G5",
            passed=True,
            detail="no log — ratio N/A",
            data={"intent_to_commit_ratio": None},
        )
    rows: List[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    proposals = sum(1 for r in rows if r.get("event_type") == "proposal")
    commits = sum(1 for r in rows if r.get("event_type") == "commit")
    ratio = round(commits / proposals, 4) if proposals else None
    by_kind: Dict[str, int] = {}
    for row in rows:
        if row.get("event_type") != "proposal":
            continue
        kind = (row.get("payload") or {}).get("write_intent_kind") or "unknown"
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return GateResult(
        gate_id="G5",
        passed=True,
        detail=f"intent/commit ratio={ratio} proposals={proposals} commits={commits}",
        data={
            "proposals": proposals,
            "commits": commits,
            "intent_to_commit_ratio": ratio,
            "by_kind": by_kind,
        },
    )


def run_cp15_gates(*, base_dir: Optional[Path] = None) -> CP15GateReport:
    log_path = Path(base_dir or ROOT) / "observability" / "gtbs_transactions.jsonl"
    report = CP15GateReport()
    report.results.append(_adapter_wiring_ok())
    report.results.append(_analyze_log(log_path))
    report.results.append(_gate_g2_from_log(log_path))
    report.results.extend(_gate_g3_g4())
    report.results.append(_gate_g5(log_path))
    return report
