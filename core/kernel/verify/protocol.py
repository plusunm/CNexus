"""
Kernel Final Verification Protocol (KFVP) — CP-3 closure audit.

Static scan + env contract → weighted closure score (0–100).
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional

KERNEL_VERIFY_VERSION = "kernel-final-verify-v1"

# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS = {
    "kernel_entry_purity": 0.25,
    "execution_record_completeness": 0.20,
    "identity_consistency": 0.15,
    "replay_determinism": 0.15,
    "ui_projection_purity": 0.25,
}


class Severity(str, Enum):
    BLOCKER = "blocker"
    WARN = "warn"
    INFO = "info"


class Dimension(str, Enum):
    KERNEL_ENTRY = "kernel_entry_purity"
    RECORD = "execution_record_completeness"
    IDENTITY = "identity_consistency"
    REPLAY = "replay_determinism"
    UI = "ui_projection_purity"


DEDUCTIONS = {
    Severity.BLOCKER: 12,
    Severity.WARN: 5,
    Severity.INFO: 2,
}


@dataclass
class Finding:
    id: str
    dimension: Dimension
    severity: Severity
    message: str
    path: str = ""
    evidence: str = ""


@dataclass
class DimensionScore:
    dimension: str
    score: float
    findings: list[Finding] = field(default_factory=list)


@dataclass
class VerificationReport:
    version: str = KERNEL_VERIFY_VERSION
    closure_score: float = 0.0
    status: str = "UNKNOWN"
    dimensions: list[DimensionScore] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    env: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def _scan_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        out.extend(root.glob(pat))
    return sorted({p for p in out if p.is_file()})


class KernelFinalVerificationProtocol:
    """Full-repo static verification for CP-3 single-truth closure."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or _repo_root()
        self.findings: list[Finding] = []

    def run(self) -> VerificationReport:
        self.findings = []
        self._check_env_contract()
        self._scan_api_bypass()
        self._scan_core_dual_truth()
        self._scan_legacy_artifacts()
        self._scan_ui_projection()
        self._scan_record_completeness()
        self._scan_observe_compliance_ast()
        dimensions = self._score_dimensions()
        closure = sum(d.score * DIMENSION_WEIGHTS[d.dimension] for d in dimensions)
        blockers = sum(1 for f in self.findings if f.severity == Severity.BLOCKER)
        warns = sum(1 for f in self.findings if f.severity == Severity.WARN)
        status = "CLOSED" if closure >= 85 and blockers == 0 else "PARTIAL" if closure >= 55 else "OPEN"
        return VerificationReport(
            closure_score=round(closure, 1),
            status=status,
            dimensions=dimensions,
            findings=self.findings,
            env=self._env_snapshot(),
            summary={"blockers": blockers, "warnings": warns, "total": len(self.findings)},
        )

    def _add(
        self,
        fid: str,
        dimension: Dimension,
        severity: Severity,
        message: str,
        *,
        path: str = "",
        evidence: str = "",
    ) -> None:
        self.findings.append(
            Finding(
                id=fid,
                dimension=dimension,
                severity=severity,
                message=message,
                path=path,
                evidence=evidence[:240],
            )
        )

    def _env_snapshot(self) -> dict[str, Any]:
        from core.kernel.enforce.mode import enforce_mode, hard_lock_mode, legacy_allowed
        from core.kernel.kernel import graph_enabled, kernel_enabled

        return {
            "KERNEL_HARD_LOCK_MODE": hard_lock_mode(),
            "KERNEL_ENFORCE_MODE": enforce_mode(),
            "KERNEL_LEGACY_ALLOW": legacy_allowed(),
            "USE_EXECUTION_KERNEL": kernel_enabled(),
            "USE_EXECUTION_GRAPH": graph_enabled(),
        }

    def _check_env_contract(self) -> None:
        snap = self._env_snapshot()
        if not snap["KERNEL_HARD_LOCK_MODE"]:
            self._add(
                "env-hard-lock-off",
                Dimension.KERNEL_ENTRY,
                Severity.BLOCKER,
                "KERNEL_HARD_LOCK_MODE is disabled",
            )
        if not snap["KERNEL_ENFORCE_MODE"]:
            self._add(
                "env-enforce-off",
                Dimension.KERNEL_ENTRY,
                Severity.WARN,
                "KERNEL_ENFORCE_MODE is disabled",
            )
        if snap["KERNEL_LEGACY_ALLOW"]:
            self._add(
                "env-legacy-allowed",
                Dimension.KERNEL_ENTRY,
                Severity.BLOCKER,
                "KERNEL_LEGACY_ALLOW permits legacy execution fallback",
            )
        if not snap["USE_EXECUTION_KERNEL"]:
            self._add(
                "env-kernel-off",
                Dimension.KERNEL_ENTRY,
                Severity.BLOCKER,
                "USE_EXECUTION_KERNEL is disabled",
            )

    def _scan_api_bypass(self) -> None:
        api_roots = [
            self.root / "brain-memory-ui" / "api" / "routes",
            self.root / "api",
        ]
        blockers: list[tuple[str, str, str]] = [
            (r"get_runtime\(\)\.trait_based_reflection", "reflective direct write", "reflective.py"),
            (r"get_runtime\(\)\.reflection_pipeline\.run_due_reviews", "reflective scheduler bypass", "reflective.py"),
            (r"get_runtime\(\)\.run_memory_maintenance", "memory maintenance bypass", "memory.py"),
            (r"get_runtime\(\)\.run_validation_suite", "governance validation bypass", "governance.py"),
            (r"get_runtime\(\)\.process_capture_cognition", "capture cognition side-effect", "memory.py"),
            (r"runtime\.process_capture_cognition", "capture cognition side-effect", "memory.py"),
            (r"runtime\.run_memory_maintenance", "memory maintenance bypass", "memory.py"),
            (r"runtime\.run_validation_suite", "governance validation bypass", "governance.py"),
            (r"runtime\.trait_based_reflection", "reflective direct write", "reflective.py"),
            (r"runtime\.reflection_pipeline\.run_due_reviews", "reflective scheduler bypass", "reflective.py"),
        ]
        warns: list[tuple[str, str, str]] = [
            (r"get_runtime\(\)\.get_current_state", "runtime state as truth", "governance.py"),
            (r"get_runtime\(\)\.cdg\.trajectory_report", "cdg trajectory direct read", "governance.py"),
            (r"get_runtime\(\)\.memory_stats", "memory stats direct read", "memory.py"),
        ]

        for api_root in api_roots:
            if not api_root.exists():
                continue
            for path in _scan_files(api_root, ["*.py"]):
                source = _read(path)
                rel = _rel(path, self.root)
                for pattern, msg, hint in blockers:
                    if hint not in path.name and hint != path.name:
                        continue
                    m = re.search(pattern, source)
                    if m:
                        self._add(
                            f"api-bypass-{path.stem}-{pattern[:20]}",
                            Dimension.KERNEL_ENTRY,
                            Severity.BLOCKER,
                            f"API bypass: {msg}",
                            path=rel,
                            evidence=m.group(0),
                        )
                for pattern, msg, hint in warns:
                    if hint not in path.name:
                        continue
                    m = re.search(pattern, source)
                    if m:
                        self._add(
                            f"api-read-{path.stem}",
                            Dimension.KERNEL_ENTRY,
                            Severity.WARN,
                            f"API direct runtime read: {msg}",
                            path=rel,
                            evidence=m.group(0),
                        )

        ws = self.root / "api" / "ws_routes.py"
        if ws.exists():
            source = _read(ws)
            if re.search(r"runtime\.process_interaction\s*\(", source):
                if "_legacy_adapter_provider" not in source:
                    self._add(
                        "ws-interact-bypass",
                        Dimension.KERNEL_ENTRY,
                        Severity.BLOCKER,
                        "/ws/interact calls runtime.process_interaction without legacy adapter guard",
                        path=_rel(ws, self.root),
                    )
                else:
                    self._add(
                        "ws-interact-fallback",
                        Dimension.KERNEL_ENTRY,
                        Severity.WARN,
                        "/ws/interact retains runtime.process_interaction fallback when adapter unset",
                        path=_rel(ws, self.root),
                    )

        handler = self.root / "core" / "openai_compat" / "handler.py"
        if handler.exists():
            source = _read(handler)
            if re.search(r"runtime\.process_interaction\s*\(", source):
                self._add(
                    "openai-handler-fallback",
                    Dimension.KERNEL_ENTRY,
                    Severity.WARN,
                    "OpenAI handler retains direct runtime.process_interaction when legacy_adapter is None",
                    path=_rel(handler, self.root),
                )

    def _scan_core_dual_truth(self) -> None:
        hooks = self.root / "core" / "kernel" / "hooks.py"
        if hooks.exists():
            source = _read(hooks)
            if "core.spine.identity" in source and "graph_identity" not in source:
                self._add(
                    "dual-identity-hooks",
                    Dimension.IDENTITY,
                    Severity.WARN,
                    "kernel hooks resolve spine identity store (parallel to graph identity)",
                    path=_rel(hooks, self.root),
                )
            if "get_identity_service" in source:
                self._add(
                    "spine-identity-service",
                    Dimension.IDENTITY,
                    Severity.WARN,
                    "kernel hooks still wire spine ExecutionIdentityService",
                    path=_rel(hooks, self.root),
                )

        graph_id = self.root / "core" / "kernel" / "identity" / "graph_identity_v1.py"
        spine_id = self.root / "core" / "spine" / "identity" / "kernel.py"
        if graph_id.exists() and spine_id.exists():
            self._add(
                "dual-identity-kernels",
                Dimension.IDENTITY,
                Severity.WARN,
                "Parallel identity kernels: graph_identity_v1 + spine identity kernel",
                path="core/kernel/identity + core/spine/identity",
            )

        ir_route = self.root / "brain-memory-ui" / "api" / "routes" / "ir.py"
        if ir_route.exists() and "replay_strict" in _read(ir_route):
            self._add(
                "dual-replay-ir",
                Dimension.REPLAY,
                Severity.WARN,
                "IR route exposes replay_strict (parallel to kernel replay)",
                path=_rel(ir_route, self.root),
            )

        spine_query = self.root / "core" / "spine" / "query" / "builder_v3.py"
        if spine_query.exists() and "get_identity_service" in _read(spine_query):
            self._add(
                "spine-query-truth",
                Dimension.IDENTITY,
                Severity.WARN,
                "Spine query builder uses spine identity service as truth",
                path=_rel(spine_query, self.root),
            )

    def _scan_legacy_artifacts(self) -> None:
        dispatch = self.root / "core" / "control_plane" / "dispatch.py"
        if dispatch.exists() and "_execute_legacy" in _read(dispatch):
            self._add(
                "legacy-execute-artifact",
                Dimension.KERNEL_ENTRY,
                Severity.INFO,
                "_execute_legacy() still present (runtime-gated, not compile-deleted)",
                path=_rel(dispatch, self.root),
            )

        proxy = self.root / "core" / "kernel" / "migration" / "runtime_proxy.py"
        if proxy.exists() and "BYPASS_KERNEL" in _read(proxy):
            self._add(
                "bypass-kwarg-artifact",
                Dimension.KERNEL_ENTRY,
                Severity.INFO,
                "RuntimeProxy BYPASS_KERNEL kwarg still exists (hard-lock raises)",
                path=_rel(proxy, self.root),
            )

    def _scan_ui_projection(self) -> None:
        fe = self.root / "brain-memory-ui" / "frontend"
        if not fe.exists():
            return

        projection_lock = fe / "lib" / "projectionLock.ts"
        kernel_record = fe / "lib" / "kernelRecord.ts"
        if projection_lock.exists():
            self._add(
                "ui-projection-lock-present",
                Dimension.UI,
                Severity.INFO,
                "UI projection lock module present",
                path=_rel(projection_lock, self.root),
            )
        else:
            self._add(
                "ui-projection-lock-missing",
                Dimension.UI,
                Severity.BLOCKER,
                "projectionLock.ts missing",
            )

        if not kernel_record.exists():
            self._add(
                "ui-kernel-record-missing",
                Dimension.UI,
                Severity.BLOCKER,
                "kernelRecord.ts missing",
            )

        spine_sources = [
            (fe / "lib" / "spine" / "api.ts", r"spine/query", "spine query API"),
            (fe / "hooks" / "useExplainStream.ts", r"spine/stream", "explain WS stream"),
            (fe / "hooks" / "useSpineStream.ts", r"gtbs", "GTBS spine stream"),
            (fe / "lib" / "token" / "api.ts", r"runtime/introspect", "runtime introspect"),
            (fe / "lib" / "api.ts", r"/v1/cse/", "CSE live API"),
        ]
        for path, pattern, label in spine_sources:
            if not path.exists():
                continue
            source = _read(path)
            if pattern in source or re.search(pattern, source):
                self._add(
                    f"ui-alt-source-{path.stem}",
                    Dimension.UI,
                    Severity.WARN,
                    f"Alternate UI truth source still wired: {label}",
                    path=_rel(path, self.root),
                )

        if projection_lock.exists():
            pl_source = _read(projection_lock)
            if "DEBUG_SPINE" in pl_source or "debugSpineEnabled" in pl_source:
                self._add(
                    "ui-debug-spine-escape",
                    Dimension.UI,
                    Severity.WARN,
                    "DEBUG_SPINE escape hatch allows spine panels under projection lock",
                    path=_rel(projection_lock, self.root),
                )

        exec_view = fe / "components" / "mind" / "query" / "ExecutionSpineView.tsx"
        if exec_view.exists():
            source = _read(exec_view)
            if "fetchExecutionRecord" not in source and "kernelRecord" not in source:
                self._add(
                    "ui-exec-view-not-projected",
                    Dimension.UI,
                    Severity.WARN,
                    "ExecutionSpineView does not reference kernel record projection",
                    path=_rel(exec_view, self.root),
                )
            if "useExplainStream" in source:
                self._add(
                    "ui-explain-stream-import",
                    Dimension.UI,
                    Severity.INFO,
                    "ExecutionSpineView still imports useExplainStream (gated by projection lock)",
                    path=_rel(exec_view, self.root),
                )

        debugger = fe / "components" / "mind" / "debugger" / "DebuggerLayout.tsx"
        if debugger.exists() and "useSpineStream" in _read(debugger):
            self._add(
                "ui-debugger-spine",
                Dimension.UI,
                Severity.WARN,
                "DebuggerLayout still consumes GTBS/spine stream (non-projection)",
                path=_rel(debugger, self.root),
            )

    def _scan_record_completeness(self) -> None:
        record_py = self.root / "core" / "kernel" / "record.py"
        if not record_py.exists():
            self._add(
                "record-module-missing",
                Dimension.RECORD,
                Severity.BLOCKER,
                "ExecutionRecord module missing",
            )
            return

        source = _read(record_py)
        required_fields = ["identity", "graph", "derivation", "replay_signature", "audit"]
        for fld in required_fields:
            if fld not in source:
                self._add(
                    f"record-field-{fld}",
                    Dimension.RECORD,
                    Severity.WARN,
                    f"ExecutionRecord missing or incomplete field: {fld}",
                    path=_rel(record_py, self.root),
                )

        missing_projections = ["state", "explain", "replay"]
        for proj in missing_projections:
            if f"{proj}:" not in source and f'"{proj}"' not in source:
                self._add(
                    f"record-projection-{proj}",
                    Dimension.RECORD,
                    Severity.WARN,
                    f"ExecutionRecord lacks dedicated {proj} projection slot",
                    path=_rel(record_py, self.root),
                )

        kernel_py = self.root / "core" / "kernel" / "kernel.py"
        if kernel_py.exists() and "get_record" not in _read(kernel_py):
            self._add(
                "kernel-record-store",
                Dimension.RECORD,
                Severity.WARN,
                "ExecutionKernel may lack durable record retrieval",
                path=_rel(kernel_py, self.root),
            )

    def _scan_observe_compliance_ast(self) -> None:
        from core.kernel.verify.compliance import (
            OBSERVE_LEAK_BASELINE,
            list_baseline_observe_leaks,
            scan_observe_leaks,
        )

        for hit in list_baseline_observe_leaks(self.root):
            self._add(
                f"observe-leak-baseline-{Path(hit.path).stem}-{hit.lineno}",
                Dimension.KERNEL_ENTRY,
                Severity.WARN,
                f"Baseline observe leak (grandfathered): get_runtime().{hit.method}()",
                path=hit.path,
                evidence=hit.evidence,
            )

        for hit in scan_observe_leaks(self.root, include_baseline=False):
            self._add(
                f"observe-leak-{Path(hit.path).stem}-{hit.lineno}",
                Dimension.KERNEL_ENTRY,
                Severity.BLOCKER,
                f"Observability compliance: forbidden get_runtime().{hit.method}() outside core/kernel/",
                path=hit.path,
                evidence=hit.evidence,
            )

        # Document baseline count for audit trail.
        if OBSERVE_LEAK_BASELINE:
            self._add(
                "observe-leak-baseline-count",
                Dimension.KERNEL_ENTRY,
                Severity.INFO,
                f"Observe leak baseline files frozen: {len(OBSERVE_LEAK_BASELINE)}",
            )

    def _score_dimensions(self) -> list[DimensionScore]:
        scores: list[DimensionScore] = []
        for dim_key in DIMENSION_WEIGHTS:
            dim = Dimension(dim_key)
            dim_findings = [f for f in self.findings if f.dimension == dim]
            deduction = sum(DEDUCTIONS[f.severity] for f in dim_findings)
            raw = max(0.0, 100.0 - deduction)
            scores.append(DimensionScore(dimension=dim_key, score=round(raw, 1), findings=dim_findings))
        return scores


def run_verification(project_root: Optional[Path] = None) -> VerificationReport:
    return KernelFinalVerificationProtocol(project_root).run()


def format_report(report: VerificationReport) -> str:
    lines = [
        f"CNexus Kernel Final Verification ({report.version})",
        f"Closure Score: {report.closure_score}/100  [{report.status}]",
        f"Findings: {report.summary.get('blockers', 0)} blockers, "
        f"{report.summary.get('warnings', 0)} warnings, "
        f"{report.summary.get('total', 0)} total",
        "",
        "Dimensions:",
    ]
    for dim in report.dimensions:
        lines.append(f"  - {dim.dimension}: {dim.score}/100 ({len(dim.findings)} findings)")
    lines.append("")
    lines.append("Environment:")
    for k, v in report.env.items():
        lines.append(f"  {k}={v}")
    if report.findings:
        lines.append("")
        lines.append("Top findings:")
        ordered = sorted(
            report.findings,
            key=lambda f: (0 if f.severity == Severity.BLOCKER else 1 if f.severity == Severity.WARN else 2),
        )
        for f in ordered[:12]:
            loc = f" @ {f.path}" if f.path else ""
            lines.append(f"  [{f.severity.value}] {f.id}: {f.message}{loc}")
    return "\n".join(lines)
