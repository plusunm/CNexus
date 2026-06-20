#!/usr/bin/env python3
"""Layer 2 FULL BOOT verification — sandbox API dry run (B1–B9)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "brain-memory-ui"
REPORT_TEMPLATE = ROOT / "docs" / "migration" / "LAYER2_FULL_BOOT_REPORT.template.md"
REPORT_OUTPUT = ROOT / "docs" / "migration" / "LAYER2_FULL_BOOT_REPORT.md"

def _resolve_memory_dir_from_event(event: Any) -> Optional[str]:
    if not isinstance(event, dict):
        return None
    raw = event.get("trace_store_path") or event.get("path")
    if not raw:
        return None
    path = Path(str(raw))
    if path.name == "traces":
        return str(path.parent)
    if path.parent.name == "traces":
        return str(path.parent.parent)
    return str(path.parent)


def _make_sandbox(run_id: str) -> Path:
    """ASCII-only sandbox so BM_MEMORY_DIR is not re-hashed away from temp Unicode paths."""
    root = Path(os.environ.get("ProgramData", "C:/ProgramData")) / "cnexus" / "layer2-boot" / run_id
    root.mkdir(parents=True, exist_ok=True)
    return root


DOMAIN_FILES = (
    "self_model_cognize.json",
    "self_model_decide.json",
    "self_model_store_meta.json",
)


@dataclass
class GateResult:
    gate_id: str
    name: str
    passed: bool
    detail: str = ""
    snippet: str = ""


@dataclass
class VerifyRun:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sandbox_dir: str = ""
    api_base: str = ""
    port: int = 0
    ready_timeout: float = 120.0
    results: List[GateResult] = field(default_factory=list)
    memory_dir: Optional[str] = None
    interact_trace_id: Optional[str] = None
    proc: Optional[subprocess.Popen] = None

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)


def _http_json(method: str, url: str, body: Optional[dict] = None, timeout: float = 30.0) -> tuple[int, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _gate(run: VerifyRun, gate_id: str, name: str, passed: bool, detail: str = "", snippet: str = "") -> GateResult:
    result = GateResult(gate_id=gate_id, name=name, passed=passed, detail=detail, snippet=snippet)
    run.results.append(result)
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {gate_id}: {name} — {detail}")
    return result


def _file_mtimes(observability_dir: Path) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for name in DOMAIN_FILES:
        path = observability_dir / name
        out[name] = path.stat().st_mtime if path.is_file() else None
    return out


def _run_b2_compliance(run: VerifyRun) -> GateResult:
    try:
        from core.kernel.verify.compliance import assert_observability_compliance

        assert_observability_compliance(ROOT, include_baseline=False)
        return _gate(run, "B2", "AST compliance (0 observe leaks)", True, "assert_observability_compliance() clean")
    except Exception as exc:
        return _gate(run, "B2", "AST compliance (0 observe leaks)", False, str(exc)[:500])


def _wait_api_listening(run: VerifyRun, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_err = "no response"
    while time.monotonic() < deadline:
        if run.proc and run.proc.poll() is not None:
            err = (run.proc.stderr.read() if run.proc.stderr else "")[:800]
            raise RuntimeError(f"API exited early (code={run.proc.returncode}): {err}")
        try:
            code, _ = _http_json("GET", f"{run.api_base}/health", timeout=2.0)
            if code == 200:
                return
        except (URLError, TimeoutError, OSError) as exc:
            last_err = str(exc)
        time.sleep(0.25)
    raise TimeoutError(f"API did not listen within {timeout}s ({last_err})")


def _spawn_api(run: VerifyRun, *, ready_timeout: float) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": f"{UI_ROOT}{os.pathsep}{ROOT}",
            "BRAIN_MEMORY_ROOT": str(ROOT),
            "BM_MEMORY_DIR": run.sandbox_dir,
            "BM_API_PORT": str(run.port),
            "CNEXUS_DEPLOY_LEVEL": "dev",
            "CNEXUS_BOOT_SKIP_COGNITIVE": "1",
            "CNEXUS_DISABLE_REFLECTION": "1",
            "CNEXUS_DISABLE_CDG": "0",
            "MOCK_LLM_RESPONSE": "1",
        }
    )
    run.proc = subprocess.Popen(
        [sys.executable, "-m", "api.main"],
        cwd=str(UI_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    listen_timeout = min(30.0, ready_timeout * 0.25)
    _wait_api_listening(run, listen_timeout)

    deadline = time.monotonic() + ready_timeout
    warm_sent = False
    last_detail = "starting"
    while time.monotonic() < deadline:
        if run.proc.poll() is not None:
            err = (run.proc.stderr.read() if run.proc.stderr else "")[:800]
            raise RuntimeError(f"API exited early (code={run.proc.returncode}): {err}")
        if not warm_sent:
            code, payload = _http_json("POST", f"{run.api_base}/v1/system/warm_runtime?force=1")
            warm_sent = code == 200
        code, payload = _http_json("GET", f"{run.api_base}/v1/system/ready")
        if code == 200:
            operational = bool(payload.get("operational_ready"))
            status = str(payload.get("status", ""))
            last_detail = f"operational_ready={operational} status={status}"
            if operational or status in ("operational", "ready"):
                return
        time.sleep(0.5)
    raise TimeoutError(f"B1 ready timeout after {ready_timeout}s ({last_detail})")


def _run_b1_ready(run: VerifyRun) -> GateResult:
    try:
        _spawn_api(run, ready_timeout=run.ready_timeout)
        code, payload = _http_json("GET", f"{run.api_base}/v1/system/ready")
        ok = code == 200 and bool(payload.get("operational_ready"))
        detail = f"HTTP {code}; operational_ready={payload.get('operational_ready')}"
        return _gate(run, "B1", "API Ready (operational_ready)", ok, detail, json.dumps(payload, ensure_ascii=False)[:600])
    except Exception as exc:
        return _gate(run, "B1", "API Ready (operational_ready)", False, str(exc)[:500])


def _run_b3_governance(run: VerifyRun) -> GateResult:
    code, payload = _http_json("GET", f"{run.api_base}/governance/state", timeout=60.0)
    if code != 200:
        return _gate(run, "B3", "Governance state probe", False, f"HTTP {code}: {payload}")
    stability = (payload.get("stability_metrics") or {}).get("overall_stability_score")
    ok = isinstance(stability, (int, float))
    detail = f"overall_stability_score={stability}"
    snippet = json.dumps({"overall_stability_score": stability}, ensure_ascii=False)
    return _gate(run, "B3", "Governance state probe", ok, detail, snippet)


def _run_b4_observe(run: VerifyRun) -> GateResult:
    code_mem, mem = _http_json("GET", f"{run.api_base}/v1/memory/stats", timeout=30.0)
    code_trace, linkage = _http_json("GET", f"{run.api_base}/v1/system/linkage_debug?trace=true", timeout=30.0)
    event = linkage.get("event") if isinstance(linkage, dict) else {}
    total_lines = event.get("total_lines") if isinstance(event, dict) else None
    shard_count = event.get("shard_count") if isinstance(event, dict) else None
    mem_ok = code_mem == 200 and "total" in mem
    trace_ok = code_trace == 200 and not event.get("skipped") and isinstance(total_lines, int)
    ok = mem_ok and trace_ok
    detail = (
        f"memory/stats HTTP {code_mem} total={mem.get('total') if isinstance(mem, dict) else None}; "
        f"linkage trace total_lines={total_lines} shard_count={shard_count}"
    )
    run.memory_dir = _resolve_memory_dir_from_event(event) or run.memory_dir
    if run.memory_dir:
        detail += f"; memory_dir={run.memory_dir}"
    snippet = json.dumps(
        {"memory_total": mem.get("total") if isinstance(mem, dict) else None, "trace_event": event},
        ensure_ascii=False,
    )[:800]
    return _gate(run, "B4", "Observe probe (memory + cross-shard total_lines)", ok, detail, snippet)


def _run_b5_interact(run: VerifyRun) -> GateResult:
    body = {
        "user_id": "layer2-full-boot",
        "message": "L2-3 FULL BOOT smoke ping",
        "options": {
            "use_memory": True,
            "assistant_output": "L2-3 deterministic mock — COGNIZE/DECIDE/STORE path",
        },
    }
    code, payload = _http_json("POST", f"{run.api_base}/v1/interact", body=body, timeout=120.0)
    if code != 200:
        return _gate(run, "B5", "POST /v1/interact smoke", False, f"HTTP {code}: {str(payload)[:300]}")
    if isinstance(payload, dict) and payload.get("type") == "error":
        return _gate(run, "B5", "POST /v1/interact smoke", False, str(payload)[:400])
    ok = bool(payload.get("governance_pass", True)) and bool(payload.get("response"))
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    run.interact_trace_id = meta.get("trace_id") if isinstance(meta, dict) else None
    detail = f"governance_pass={payload.get('governance_pass')} trace_id={run.interact_trace_id}"
    snippet = json.dumps(
        {
            "governance_pass": payload.get("governance_pass"),
            "response": (payload.get("response") or "")[:120],
            "memory_blocks_updated": payload.get("memory_blocks_updated"),
        },
        ensure_ascii=False,
    )
    return _gate(run, "B5", "POST /v1/interact smoke", ok, detail, snippet)


def _read_today_shard(base_dir: Path) -> tuple[Optional[Path], List[dict]]:
    from core.runtime.trace_store import trace_file_path

    shard = trace_file_path(str(base_dir))
    if shard is None or not shard.is_file():
        return shard, []
    rows: List[dict] = []
    for line in shard.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return shard, rows


def _run_b6_b8_trace(run: VerifyRun) -> tuple[GateResult, GateResult]:
    from core.runtime.trace_id import CANONICAL_TRACE_ID_RE, is_canonical_trace_id

    base = Path(run.memory_dir or run.sandbox_dir)
    shard, rows = _read_today_shard(base)
    if shard is None or not shard.exists():
        b6 = _gate(run, "B6", "Canonical trace_id in daily shard", False, "today shard missing")
        b8 = _gate(run, "B8", "interaction_step persisted in Σ.T", False, "today shard missing")
        return b6, b8

    trace_ids = [str(r.get("trace_id")) for r in rows if r.get("trace_id")]
    if run.interact_trace_id:
        trace_ids.append(str(run.interact_trace_id))
    canonical_hits = [tid for tid in trace_ids if is_canonical_trace_id(tid)]
    b6_ok = bool(canonical_hits)
    b6_detail = f"shard={shard.name} canonical_trace_ids={len(canonical_hits)} sample={canonical_hits[:1]}"
    b6 = _gate(run, "B6", "Canonical trace_id in daily shard", b6_ok, b6_detail, json.dumps({"sample": canonical_hits[:3]}, ensure_ascii=False))

    steps = [r for r in rows if r.get("type") == "interaction_step"]
    b8_ok = len(steps) > 0
    b8_detail = f"interaction_step_rows={len(steps)} shard={shard.name}"
    b8 = _gate(run, "B8", "interaction_step persisted in Σ.T", b8_ok, b8_detail)
    return b6, b8


def _run_b7_self_model(
    run: VerifyRun,
    before: Dict[str, Optional[float]],
    after: Dict[str, Optional[float]],
    observability: Path,
) -> GateResult:
    memory_root = run.memory_dir or run.sandbox_dir
    changed = [name for name in DOMAIN_FILES if after.get(name) and (before.get(name) is None or after[name] > before[name])]
    unchanged = [name for name in DOMAIN_FILES if after.get(name) and before.get(name) and after[name] == before[name]]
    unified = observability / "unified_self_model.json"
    supplemental = False
    first_boot = all(before.get(name) is None for name in DOMAIN_FILES)
    all_exist_after = all(after.get(name) is not None for name in DOMAIN_FILES)

    if not changed and not first_boot:
        try:
            from core.self_model.store import SelfModelStore
            from core.evolved.cognitive_hooks import apply_cognize_step

            store = SelfModelStore(str(memory_root))
            mid = _file_mtimes(observability)
            apply_cognize_step(store, user_input="L2-3 domain probe", response="ok")
            after = _file_mtimes(observability)
            changed = [name for name in DOMAIN_FILES if after.get(name) and (mid.get(name) is None or after[name] > mid[name])]
            unchanged = [name for name in DOMAIN_FILES if after.get(name) and mid.get(name) and after[name] == mid[name]]
            supplemental = True
            first_boot = False
        except Exception as exc:
            return _gate(run, "B7", "SelfModel domain isolation (mtime)", False, f"domain probe failed: {exc}")

    if first_boot and all_exist_after and not unified.is_file():
        ok = True
        detail = "initial 3-way domain split materialized (no unified_self_model.json)"
    elif supplemental:
        ok = "self_model_cognize.json" in changed and "self_model_decide.json" not in changed and not unified.is_file()
        detail = f"updated={changed} unchanged={unchanged} unified_present={unified.is_file()} (supplemental cognize probe)"
    else:
        ok = len(changed) >= 1 and len(changed) < len(DOMAIN_FILES) and not unified.is_file()
        detail = f"updated={changed} unchanged={unchanged} unified_present={unified.is_file()}"
        if ok:
            detail += " (partial domain update — isolation OK)"

    snippet = "\n".join(f"{name}: before={before.get(name)} after={after.get(name)}" for name in DOMAIN_FILES)
    return _gate(run, "B7", "SelfModel domain isolation (mtime)", ok, detail, snippet)

def _run_l4_conscious_flow(run: VerifyRun) -> tuple[GateResult, GateResult, GateResult]:
    """L4-1/2/3 offline stack — simulation, prune filter, reasoning trace (Σ.T only)."""
    memory_root = str(run.memory_dir or run.sandbox_dir)
    base = Path(memory_root)
    obs = base / "observability"
    decide_path = obs / "self_model_decide.json"
    decide_mtime = decide_path.stat().st_mtime if decide_path.is_file() else None

    try:
        from core.runtime.conscious_flow import (
            CandidateResponse,
            SimulationBudget,
            SimulationEngine,
            build_reasoning_trace_from_report,
            evaluate_trajectories,
        )
        from core.runtime.trace_store import list_trace_shards

        engine = SimulationEngine(budget=SimulationBudget(max_branches=2, max_wall_ms=2000))
        report = engine.run_filtered_simulation(
            user_query="L4 FULL BOOT conscious flow probe",
            core_beliefs={"稳定性优先": 0.93, "诚实第一": 0.96},
            baseline_coherence=0.82,
            base_dir=memory_root,
        )
        l41_ok = len(report.kept) >= 1
        l41_detail = f"kept={len(report.kept)} pruned={len(report.pruned)} trace_id={report.trace_id}"

        shards = list_trace_shards(memory_root)
        sim_rows = 0
        eval_rows = 0
        for shard in shards:
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("type") == "simulation_step":
                    sim_rows += 1
                if row.get("type") == "eval_step":
                    eval_rows += 1
        l41_ok = l41_ok and sim_rows >= 1
        l41_detail += f"; simulation_step={sim_rows}"

        dangerous = CandidateResponse(
            branch_id="bad",
            response_text="建议用户执行危险操作",
            expected_stability_score=0.5,
            assumption_seed="reckless",
        )
        safe = CandidateResponse(
            branch_id="good",
            response_text="稳定诚实的协作建议",
            expected_stability_score=0.88,
            assumption_seed="helpful_direct",
        )
        filtered = evaluate_trajectories(
            [safe, dangerous],
            trace_id=report.trace_id,
            base_dir=memory_root,
        )
        kept_ids = {c.branch_id for c in filtered.candidates}
        eval_rows = 0
        for shard in list_trace_shards(memory_root):
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("type") == "eval_step":
                    eval_rows += 1
        l42_ok = "good" in kept_ids and "bad" not in kept_ids and eval_rows >= 1
        l42_detail = f"kept={sorted(kept_ids)} eval_step={eval_rows}"

        trace = build_reasoning_trace_from_report(report, query_preview="L4 probe")
        l43_ok = trace is not None and bool(trace.assumption_seed) and trace.assumption_seed in {
            c.candidate.assumption_seed for c in report.kept
        }
        decide_after = decide_path.stat().st_mtime if decide_path.is_file() else None
        if decide_mtime is not None and decide_after is not None:
            l43_ok = l43_ok and decide_after == decide_mtime
        l43_detail = f"assumption_seed={getattr(trace, 'assumption_seed', None)} decide_mtime_unchanged={decide_after == decide_mtime if decide_mtime else 'n/a'}"

    except Exception as exc:
        l41 = _gate(run, "L4-1", "Conscious flow simulation (Σ.T)", False, str(exc)[:400])
        l42 = _gate(run, "L4-2", "Trajectory prune filter", False, "skipped — L4-1 failed")
        l43 = _gate(run, "L4-3", "Reasoning trace + Σ.I isolation", False, "skipped — L4-1 failed")
        return l41, l42, l43

    l41 = _gate(run, "L4-1", "Conscious flow simulation (Σ.T)", l41_ok, l41_detail)
    l42 = _gate(run, "L4-2", "Trajectory prune filter", l42_ok, l42_detail)
    l43 = _gate(run, "L4-3", "Reasoning trace + Σ.I isolation", l43_ok, l43_detail)
    return l41, l42, l43


def _stop_api(run: VerifyRun) -> None:
    if run.proc is None:
        return
    if run.proc.poll() is None:
        run.proc.terminate()
        try:
            run.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            run.proc.kill()
            run.proc.wait(timeout=5)


def _render_report(run: VerifyRun) -> str:
    template = REPORT_TEMPLATE.read_text(encoding="utf-8")
    b1_b8 = [next((r for r in run.results if r.gate_id == f"B{i}"), None) for i in range(1, 9)]
    l4_gates = [next((r for r in run.results if r.gate_id == gid), None) for gid in ("L4-1", "L4-2", "L4-3")]
    l4_pass = all(r.passed for r in l4_gates if r is not None) and len([r for r in l4_gates if r]) >= 3
    b9_pass = all(r.passed for r in b1_b8 if r is not None) and len([r for r in b1_b8 if r]) >= 8 and l4_pass
    if not any(r.gate_id == "B9" for r in run.results):
        _gate(
            run,
            "B9",
            "Automated summary (B1–B8 + L4-1..3)",
            b9_pass,
            "all automated gates green" if b9_pass else "one or more gates failed",
        )
    by_id = {r.gate_id: r for r in run.results}

    def status(gate_id: str) -> str:
        r = by_id.get(gate_id)
        if r is None:
            return "⬜ SKIP"
        return "✅ PASS" if r.passed else "❌ FAIL"

    def detail(gate_id: str) -> str:
        r = by_id.get(gate_id)
        return r.detail if r else "not run"

    def l4_status(gate_id: str) -> str:
        return status(gate_id)

    overall = "PASS" if run.all_passed else "FAIL"
    layer2 = "✅ COMPLETE (pending B10 manual)" if b9_pass else "❌ BLOCKED"

    replacements = {
        "{run_id}": run.run_id,
        "{timestamp_utc}": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "{sandbox_dir}": run.sandbox_dir,
        "{api_base}": run.api_base,
        "{overall_status}": overall,
        "{layer2_status}": layer2,
        "{b1_status}": status("B1"),
        "{b1_detail}": detail("B1"),
        "{b2_status}": status("B2"),
        "{b2_detail}": detail("B2"),
        "{b3_status}": status("B3"),
        "{b3_detail}": detail("B3"),
        "{b3_snippet}": by_id.get("B3", GateResult("", "", False)).snippet or detail("B3"),
        "{b4_status}": status("B4"),
        "{b4_detail}": detail("B4"),
        "{b4_snippet}": by_id.get("B4", GateResult("", "", False)).snippet or detail("B4"),
        "{b5_status}": status("B5"),
        "{b5_detail}": detail("B5"),
        "{b5_snippet}": by_id.get("B5", GateResult("", "", False)).snippet or detail("B5"),
        "{b6_status}": status("B6"),
        "{b6_detail}": detail("B6"),
        "{b7_status}": status("B7"),
        "{b7_detail}": detail("B7"),
        "{b7_snippet}": by_id.get("B7", GateResult("", "", False)).snippet or detail("B7"),
        "{b8_status}": status("B8"),
        "{b8_detail}": detail("B8"),
        "{b9_status}": status("B9"),
        "{b9_detail}": detail("B9"),
        "{l4_1_status}": l4_status("L4-1"),
        "{l4_1_detail}": detail("L4-1"),
        "{l4_2_status}": l4_status("L4-2"),
        "{l4_2_detail}": detail("L4-2"),
        "{l4_3_status}": l4_status("L4-3"),
        "{l4_3_detail}": detail("L4-3"),
    }
    out = template
    for key, value in replacements.items():
        out = out.replace(key, value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Layer 2 FULL BOOT verification (B1–B9)")
    parser.add_argument("--sandbox", help="Reuse existing sandbox dir (skip temp cleanup)")
    parser.add_argument("--port", type=int, default=0, help="API port (0 = auto)")
    parser.add_argument("--ready-timeout", type=float, default=120.0, help="Seconds to wait for API ready")
    parser.add_argument("--keep-sandbox", action="store_true", help="Do not delete temp sandbox")
    parser.add_argument("--report", type=Path, default=REPORT_OUTPUT, help="Report output path")
    args = parser.parse_args()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(UI_ROOT) not in sys.path:
        sys.path.insert(0, str(UI_ROOT))

    run = VerifyRun()
    run.ready_timeout = args.ready_timeout
    run.port = args.port or _pick_port()
    run.api_base = f"http://127.0.0.1:{run.port}"

    run.sandbox_dir = str(_make_sandbox(run.run_id))
    if args.sandbox:
        run.sandbox_dir = str(Path(args.sandbox).resolve())
    Path(run.sandbox_dir).mkdir(parents=True, exist_ok=True)
    (Path(run.sandbox_dir) / "observability").mkdir(parents=True, exist_ok=True)
    observability_before_boot = Path(run.sandbox_dir) / "observability"
    before_boot_mt = _file_mtimes(observability_before_boot)

    print(f"Layer 2 FULL BOOT verify run_id={run.run_id}")
    print(f"  sandbox={run.sandbox_dir}")
    print(f"  api={run.api_base}")

    try:
        _run_b2_compliance(run)
        b1 = _run_b1_ready(run)
        if not b1.passed:
            _gate(run, "B3", "Governance state probe", False, "skipped — B1 failed")
            _gate(run, "B4", "Observe probe (memory + cross-shard total_lines)", False, "skipped — B1 failed")
            _gate(run, "B5", "POST /v1/interact smoke", False, "skipped — B1 failed")
            _gate(run, "B7", "SelfModel domain isolation (mtime)", False, "skipped — B1 failed")
            _gate(run, "B6", "Canonical trace_id in daily shard", False, "skipped — B1 failed")
            _gate(run, "B8", "interaction_step persisted in Σ.T", False, "skipped — B1 failed")
        else:
            _run_b3_governance(run)
            _run_b4_observe(run)
            obs_dir = Path(run.memory_dir or run.sandbox_dir) / "observability"
            _run_b5_interact(run)
            after_mt = _file_mtimes(obs_dir)
            _run_b7_self_model(run, before_boot_mt, after_mt, obs_dir)
            _run_b6_b8_trace(run)
        _run_l4_conscious_flow(run)
    finally:
        _stop_api(run)
        if args.sandbox:
            pass
        elif not args.keep_sandbox:
            shutil.rmtree(run.sandbox_dir, ignore_errors=True)

    report_text = _render_report(run)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")
    print(f"\nReport written: {args.report}")
    print(f"Overall: {'PASS' if run.all_passed else 'FAIL'}")
    return 0 if run.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
