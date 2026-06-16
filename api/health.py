"""Deep health probes for production readiness."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from core.paths import get_project_root, resolve_memory_dir


def shallow_health_payload(*, version: str = "0.1.0-alpha") -> Dict[str, Any]:
    return {"status": "ok", "service": "cnexus", "version": version}


def _check_path(name: str, path: Path, *, required: bool = True) -> Dict[str, Any]:
    ok = path.exists()
    return {
        "name": name,
        "ok": ok,
        "path": str(path),
        "required": required,
        "detail": "exists" if ok else "missing",
    }


def deep_health_payload(runtime: Any = None) -> Dict[str, Any]:
    """Probe storage backends and optional Ollama."""
    project_root = get_project_root(
        getattr(runtime, "project_root", None) if runtime is not None else None
    )
    memory_dir = Path(
        getattr(runtime, "base_dir", None)
        or resolve_memory_dir(project_root, "memory")
    )
    checks: Dict[str, Dict[str, Any]] = {}

    blocks_index = memory_dir / "blocks" / "index.json"
    blocks_dir = memory_dir / "blocks"
    if blocks_index.exists():
        checks["blocks"] = _check_path("blocks_index", blocks_index, required=True)
    else:
        checks["blocks"] = _check_path("blocks_dir", blocks_dir, required=True)

    lance_dir = memory_dir / "lancedb"
    lance_ok = lance_dir.exists()
    lance_detail = "exists"
    if lance_ok and runtime is not None:
        try:
            runtime.storage.vector.table.count_rows()
            lance_detail = "table_ok"
        except Exception as exc:
            lance_ok = False
            lance_detail = f"table_error:{exc.__class__.__name__}"
    checks["lance"] = {
        "name": "lance",
        "ok": lance_ok,
        "path": str(lance_dir),
        "required": True,
        "detail": lance_detail,
    }

    kuzu_dir = memory_dir / "kuzu_db"
    checks["kuzu"] = _check_path("kuzu", kuzu_dir, required=False)

    ollama_host = os.environ.get("OLLAMA_HOST")
    if runtime is not None and hasattr(runtime, "config"):
        ollama_host = ollama_host or (runtime.config or {}).get("ollama_host")
    ollama_host = ollama_host or "http://localhost:11434"
    ollama_ok = False
    ollama_detail = "skipped"
    try:
        with httpx.Client(timeout=2.0, trust_env=False) as client:
            resp = client.get(f"{ollama_host.rstrip('/')}/api/tags")
            ollama_ok = resp.status_code == 200
            ollama_detail = "reachable" if ollama_ok else f"status_{resp.status_code}"
    except Exception as exc:
        ollama_detail = f"unreachable:{exc.__class__.__name__}"
    checks["ollama"] = {
        "name": "ollama",
        "ok": ollama_ok,
        "path": ollama_host,
        "required": False,
        "detail": ollama_detail,
    }

    required_ok = all(item["ok"] for item in checks.values() if item.get("required"))
    optional_ok = all(item["ok"] for item in checks.values())
    status = "ready" if required_ok else "not_ready"
    if required_ok and not optional_ok:
        status = "degraded"

    return {
        "status": status,
        "service": "cnexus",
        "checks": checks,
        "memory_dir": str(memory_dir),
    }
