"""X3-a — AST compliance guard against observe-surface leaks via get_runtime()."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

FORBIDDEN_RUNTIME_READS = frozenset({"memory_stats", "get_current_state"})

# Grandfather list cleared after X3-b — any new leak is a hard BLOCKER.
OBSERVE_LEAK_BASELINE: frozenset[str] = frozenset()

SCAN_ROOTS = (
    "brain-memory-ui",
    "api",
    "core",
    "brain_memory",
)

SCAN_SKIP_PARTS = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "tests",
        "scripts",
        "target",
        "runtime-bundle",
        "site-packages",
    }
)


class ComplianceViolationError(Exception):
    """Raised when observability compliance scan detects a forbidden pattern."""

    def __init__(self, violations: list["ObserveLeakViolation"]) -> None:
        self.violations = violations
        lines = "\n".join(f"  {v.path}:{v.lineno} — {v.method}()" for v in violations)
        super().__init__(f"Observability compliance violation(s):\n{lines}")


@dataclass(frozen=True)
class ObserveLeakViolation:
    path: str
    lineno: int
    method: str
    evidence: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _iter_python_files(root: Path) -> Iterator[Path]:
    for scan_root in SCAN_ROOTS:
        base = root / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in SCAN_SKIP_PARTS for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if rel.startswith("core/kernel/"):
                continue
            if "frontend/src-tauri" in rel:
                continue
            yield path


def _is_get_runtime(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Name) and func.id == "get_runtime"


def _scan_source(rel_path: str, source: str) -> list[ObserveLeakViolation]:
    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError:
        return []

    violations: list[ObserveLeakViolation] = []

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in FORBIDDEN_RUNTIME_READS:
                    base = node.func.value
                    if _is_get_runtime(base) or (
                        isinstance(base, ast.Name) and base.id == "runtime"
                    ):
                        violations.append(
                            ObserveLeakViolation(
                                path=rel_path,
                                lineno=node.lineno,
                                method=node.func.attr,
                                evidence=ast.get_source_segment(source, node) or node.func.attr,
                            )
                        )
            self.generic_visit(node)

    Visitor().visit(tree)
    return violations


def scan_observe_leaks(
    project_root: Optional[Path] = None,
    *,
    include_baseline: bool = False,
) -> list[ObserveLeakViolation]:
    root = project_root or _repo_root()
    all_violations: list[ObserveLeakViolation] = []
    for path in _iter_python_files(root):
        rel = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        hits = _scan_source(rel, source)
        for hit in hits:
            if not include_baseline and rel in OBSERVE_LEAK_BASELINE:
                continue
            all_violations.append(hit)
    return sorted(all_violations, key=lambda v: (v.path, v.lineno))


def assert_observability_compliance(
    project_root: Optional[Path] = None,
    *,
    include_baseline: bool = False,
) -> None:
    violations = scan_observe_leaks(project_root, include_baseline=include_baseline)
    if violations:
        raise ComplianceViolationError(violations)


def list_baseline_observe_leaks(project_root: Optional[Path] = None) -> list[ObserveLeakViolation]:
    root = project_root or _repo_root()
    out: list[ObserveLeakViolation] = []
    for rel in sorted(OBSERVE_LEAK_BASELINE):
        path = root / rel.replace("/", "\\") if "\\" in str(root) else root / rel
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        out.extend(_scan_source(rel, source))
    return out
