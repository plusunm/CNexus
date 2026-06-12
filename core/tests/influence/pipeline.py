"""L8/G8 influence test — chat pipeline simulator (deterministic, no LLM)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.tests.influence.fixtures import INFLUENCE_TEST_META


def _write_test_config(path: Path) -> None:
    cfg = {
        "version": "1.0.0-influence-test",
        "embedding_fallback": "hash",
        "runtime_mode": "g2",
        "vector_dim": 768,
        "recall_top_k": 6,
        "importance_threshold": 0.48,
        "write_gate_threshold": 0.45,
        "enable_multi_hop": False,
        "enable_metabolic": False,
        "auto_capture": True,
        "auto_recall": True,
        "cdg": {
            "enable_gtbs_shadow": False,
            "enable_gtbs_capture": False,
        },
    }
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def make_isolated_runtime(project_root: Path) -> tuple[Any, Path, Path]:
    """Create runtime in a fresh temp data dir; returns (runtime, data_dir, config_path)."""
    from brain_memory.runtime import BrainMemoryRuntime

    data_dir = Path(tempfile.mkdtemp(prefix="cnexus_influence_"))
    cfg_path = data_dir / "influence_config.json"
    _write_test_config(cfg_path)
    prev = os.environ.get("BM_MEMORY_DIR")
    os.environ["BM_MEMORY_DIR"] = str(data_dir)
    try:
        runtime = BrainMemoryRuntime(
            config_path=str(cfg_path),
            base_dir=str(data_dir),
            project_root=str(project_root),
        )
    finally:
        if prev is None:
            os.environ.pop("BM_MEMORY_DIR", None)
        else:
            os.environ["BM_MEMORY_DIR"] = prev
    return runtime, data_dir, cfg_path


def deterministic_response(message: str, memory_context: str) -> str:
    """Stub LLM output — stable across runs with identical inputs."""
    digest = hashlib.sha256(f"{message}|{memory_context}".encode("utf-8")).hexdigest()[:16]
    return f"[stub-reply:{digest}]"


def trace_recall(runtime: Any, query: str) -> tuple[str, dict[str, Any]]:
    mode = getattr(runtime, "runtime_mode", "g2")
    recall_path = "g2_cognitive_recall" if mode == "g2" else "hybrid_recall"
    context = runtime.recall(query)
    trace = {
        "pipeline": recall_path,
        "runtime_mode": mode,
        "recall_path": recall_path,
        "context_chars": len(context),
        "use_memory": True,
    }
    return context, trace


def trace_capture(runtime: Any, role: str, content: str, *, importance: float) -> tuple[Any, dict[str, Any]]:
    capture_path = "gtbs_capture" if runtime._gtbs_capture_enabled() else "direct_capture"
    result = runtime.capture(role, content, importance=importance)
    denied = isinstance(result, str) and str(result).startswith("denied:")
    trace = {
        "capture_path": capture_path,
        "role": role,
        "importance": importance,
        "layer": "episodic",
        "denied": denied,
        "content_len": len(content),
    }
    if not denied and isinstance(result, dict):
        trace["memory_id_prefix"] = str(result.get("memory_id", result))[:8]
    return result, trace


def simulate_chat_turn(runtime: Any, message: str) -> dict[str, Any]:
    memory_context, routing_recall = trace_recall(runtime, message)
    response = deterministic_response(message, memory_context)
    _, cap_user = trace_capture(runtime, "user", message, importance=0.65)
    _, cap_asst = trace_capture(runtime, "assistant", response, importance=0.55)
    return {
        "message": message,
        "response": response,
        "memory_context_chars": len(memory_context),
        "routing_trace": [routing_recall, cap_user, cap_asst],
        "memory_trace": [cap_user, cap_asst],
    }


def read_shadow_jsonl(data_dir: Path) -> list[dict[str, Any]]:
    path = data_dir / "observability" / "gtbs_shadow.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_influence_observation(data_dir: Path, record: dict[str, Any]) -> Path:
    obs_dir = data_dir / "observability"
    obs_dir.mkdir(parents=True, exist_ok=True)
    path = obs_dir / "l8g8_influence_experiment.jsonl"
    payload = {**INFLUENCE_TEST_META, **record}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return path
