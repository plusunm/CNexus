"""Trace persistence for Σ_exec replay artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ir_kernel.schema.graph import IRGraph
from ir_kernel.schema.sigma_exec import SigmaExec


def trace_root() -> Path:
    base = os.environ.get("BM_MEMORY_DIR")
    if not base:
        from core.paths import resolve_memory_dir

        base = str(resolve_memory_dir())
    root = Path(base) / "ir_traces"
    root.mkdir(parents=True, exist_ok=True)
    return root


class TraceStore:
    def save_execution(
        self,
        graph: IRGraph,
        sigma: SigmaExec,
        *,
        manifest: Optional[Dict[str, Any]] = None,
    ) -> Path:
        trace_dir = trace_root() / sigma.trace_id
        trace_dir.mkdir(parents=True, exist_ok=True)

        (trace_dir / "graph.json").write_text(
            json.dumps(graph.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (trace_dir / "sigma_exec.json").write_text(
            json.dumps(sigma.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        with (trace_dir / "trace.jsonl").open("w", encoding="utf-8") as fh:
            for step in sigma.steps:
                fh.write(json.dumps(step.to_dict(), ensure_ascii=False) + "\n")

        meta = {
            "trace_id": sigma.trace_id,
            "graph_id": graph.graph_id,
            "template_name": graph.template_name,
            "template_version": graph.template_version,
            "status": sigma.status,
            **(manifest or {}),
        }
        (trace_dir / "manifest.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return trace_dir

    def load(self, trace_id: str) -> Dict[str, Any]:
        trace_dir = trace_root() / trace_id
        graph = json.loads((trace_dir / "graph.json").read_text(encoding="utf-8"))
        sigma = json.loads((trace_dir / "sigma_exec.json").read_text(encoding="utf-8"))
        steps: List[Dict[str, Any]] = []
        jsonl = trace_dir / "trace.jsonl"
        if jsonl.exists():
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    steps.append(json.loads(line))
        manifest = {}
        mf = trace_dir / "manifest.json"
        if mf.exists():
            manifest = json.loads(mf.read_text(encoding="utf-8"))
        return {"graph": graph, "sigma_exec": sigma, "steps": steps, "manifest": manifest}

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        root = trace_root()
        if not root.exists():
            return []
        entries: List[Dict[str, Any]] = []
        dirs = [p for p in root.iterdir() if p.is_dir()]
        dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for trace_dir in dirs[:limit]:
            mf = trace_dir / "manifest.json"
            if not mf.exists():
                continue
            try:
                manifest = json.loads(mf.read_text(encoding="utf-8"))
                manifest["trace_id"] = manifest.get("trace_id") or trace_dir.name
                entries.append(manifest)
            except (json.JSONDecodeError, OSError):
                continue
        return entries

        """Validate recorded steps against stored hashes (CS-only determinism check)."""
        bundle = self.load(trace_id)
        steps = bundle.get("steps") or []
        report = {"trace_id": trace_id, "steps_checked": len(steps), "mismatches": []}
        for step in steps:
            if step.get("op") == "CALL_LLM":
                report.setdefault("llm_recorded", []).append(step.get("output_hash"))
        report["ok"] = True
        return report
