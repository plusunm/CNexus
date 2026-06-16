"""Fast-Path v2 — progressive streaming ready (shell → local → cluster → final)."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from core.runtime.boot_protocol import boot_status, get_boot_phase

StreamCallback = Callable[[Dict[str, Any]], Awaitable[None]]


def fast_path_v2_enabled(runtime: Optional[Any] = None) -> bool:
    flag = os.environ.get("CNEXUS_FAST_PATH_V2", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if runtime is not None:
        env = getattr(runtime, "env", None)
        if isinstance(env, dict):
            return str(env.get("CNEXUS_FAST_PATH_V2", "1")).strip() not in ("0", "false", "no", "off")
    return True


def should_use_stream_ready(*, mode: str, runtime: Optional[Any]) -> bool:
    normalized = (mode or "default").strip().lower()
    if normalized == "stream":
        return True
    if normalized in ("full", "fast"):
        return False
    from core.runtime.fast_path_v3 import fast_path_v3_enabled

    if fast_path_v3_enabled(runtime):
        return False
    return fast_path_v2_enabled(runtime)


def streaming_ready_ack() -> Dict[str, Any]:
    return {
        "status": "streaming",
        "mode": "fast-path-v2",
        "render_mode": "fast_path_v2",
    }


class StreamingReady:
    """Emit progressive ready phases without blocking the caller."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime

    async def stream_ready(self, callback: StreamCallback) -> None:
        async for event in self.iter_events():
            await callback(event)

    async def iter_events(self):
        boot = boot_status()
        ws_status = "alive" if self.runtime is not None else "starting"

        yield {
            "phase": "shell",
            "status": "rendering_ui",
            "render_mode": "fast_path_v2",
            "boot_phase": get_boot_phase().value,
            "ws": ws_status,
            "ts": time.time(),
        }
        await asyncio.sleep(0.01)

        yield {
            "phase": "local",
            "status": "local_ok",
            "l3": True,
            "memory": "loading",
            "cognitive": "unknown",
            "boot": boot,
            "ts": time.time(),
        }
        await asyncio.sleep(0.05)

        cluster_status = self._cluster_phase_status()
        yield {
            "phase": "cluster",
            "status": "cluster_pending" if cluster_status != "ok" else "cluster_ok",
            "cluster": cluster_status,
            "consensus": "deferred",
            "crdt": "deferred",
            "ts": time.time(),
        }

        async for event in self._finalize():
            yield event

    async def _finalize(self):
        await asyncio.sleep(0.1)
        final_status, gate = self._final_status()
        yield {
            "phase": "final",
            "status": final_status,
            "ready": final_status == "ready",
            "boot_phase": get_boot_phase().value,
            "ws": "alive" if self.runtime is not None else "starting",
            "gate": gate,
            "ts": time.time(),
        }

    def _cluster_phase_status(self) -> str:
        try:
            from core.runtime.boot_protocol import ready_gate_snapshot

            gate = ready_gate_snapshot()
            if gate.get("cluster_ok") is True:
                return "ok"
            if gate.get("cluster_ok") is False:
                return "warming"
            return "deferred"
        except Exception:
            return "warming"

    def _final_status(self) -> tuple[str, Dict[str, Any]]:
        try:
            from core.runtime.boot_protocol import (
                evaluate_system_ready,
                fast_health_payload,
                is_runtime_warming,
                ready_gate_snapshot,
            )

            memory_ok = False
            if self.runtime is not None:
                deep = fast_health_payload(self.runtime)
                memory_status = deep.get("status", "not_ready")
                memory_ok = memory_status in ("ready", "degraded", "initializing")
            status = evaluate_system_ready(
                app_started=True,
                runtime_present=self.runtime is not None,
                runtime_warming=is_runtime_warming(),
                memory_ok=memory_ok,
            )
            gate = ready_gate_snapshot()
            slim = {
                "ready_gate_ok": gate.get("ready_gate_ok"),
                "layer": gate.get("layer"),
                "cluster_ok": gate.get("cluster_ok"),
            }
            return status, slim
        except Exception:
            return "warming", {}
