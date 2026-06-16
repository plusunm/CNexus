"""Fast-Path v3 — UI-driven compute graph; ready model obsolete."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from core.runtime.boot_protocol import boot_status, get_boot_phase


def fast_path_v3_enabled(runtime: Optional[Any] = None) -> bool:
    flag = os.environ.get("CNEXUS_FAST_PATH_V3", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if runtime is not None:
        env = getattr(runtime, "env", None)
        if isinstance(env, dict):
            return str(env.get("CNEXUS_FAST_PATH_V3", "1")).strip() not in ("0", "false", "no", "off")
    return True


def should_use_ui_driven_ready(*, mode: str, runtime: Optional[Any]) -> bool:
    normalized = (mode or "default").strip().lower()
    if normalized == "full":
        return False
    if normalized in ("fast", "stream"):
        return False
    return fast_path_v3_enabled(runtime)


def system_ready_v3_payload(
    runtime: Optional[Any],
    *,
    boot_id: str,
    app_started: bool,
    mono_start: float,
) -> Dict[str, Any]:
    uptime_ms = int((time.monotonic() - mono_start) * 1000) if app_started else 0
    ws_status = "alive" if runtime is not None else "starting"
    if runtime is None or not app_started:
        status = "warming"
    else:
        from core.runtime.boot_protocol import evaluate_system_ready, is_runtime_warming

        status = evaluate_system_ready(
            app_started=app_started,
            runtime_present=True,
            runtime_warming=is_runtime_warming(),
            memory_ok=True,
        )
    return {
        "status": status,
        "mode": "fast-path-v3",
        "architecture": "ui_driven_compute_graph",
        "isolation": "full_predictive_ui_runtime",
        "render_mode": "fast_path_v3",
        "ui": "driver",
        "boot_id": boot_id,
        "boot_phase": get_boot_phase().value,
        "ws": ws_status,
        "runtime_pointer": runtime is not None,
        "http": "listening" if app_started else "starting",
        "uptime_ms": uptime_ms,
        "version": "0.1.0-alpha",
        "ready_model": "obsolete",
        "intents": ["chat", "status", "overview"],
        "boot": boot_status(),
    }
