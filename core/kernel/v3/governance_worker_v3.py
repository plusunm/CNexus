"""Governance / L3 worker v3 — consumes event bus, executes off control plane."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from core.kernel.non_hang_kernel import get_non_hang_kernel
from core.kernel.v3.event_bus import TOPIC_L3_DONE, TOPIC_L3_TASK, get_event_bus
from core.kernel.v3.process_isolated_executor import get_process_executor
from core.kernel.v3.warmup_task_registry import dispatch_warmup_handler, is_process_safe

logger = logging.getLogger(__name__)


class GovernanceWorkerV3:
    def __init__(self) -> None:
        self.bus = get_event_bus()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._active = 0
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="cnexus-governance-v3", daemon=True)
        self._thread.start()
        logger.info("GovernanceWorkerV3 started")

    def stop(self) -> None:
        self._running = False

    def is_idle(self) -> bool:
        with self._lock:
            busy = self._active > 0
        return not busy and self.bus.is_idle()

    def _loop(self) -> None:
        while self._running:
            event = self.bus.try_get(TOPIC_L3_TASK, timeout_s=0.1)
            if event is None:
                continue
            try:
                self._execute(event)
            except Exception as exc:
                logger.warning("GovernanceWorkerV3 task failed: %s", exc)
                self.bus.publish(
                    TOPIC_L3_DONE,
                    {"label": event.get("label"), "handler": event.get("handler"), "status": "failed"},
                )

    def _execute(self, event: dict[str, Any]) -> None:
        handler = str(event.get("handler") or "")
        label = str(event.get("label") or handler)
        timeout_s = float(event.get("timeout_s") or 3.0)

        with self._lock:
            self._active += 1
        try:
            if is_process_safe(handler):
                base_dir = event.get("base_dir")
                if base_dir is None:
                    try:
                        from api.deps import peek_runtime

                        runtime = peek_runtime()
                        if runtime is not None:
                            base_dir = str(getattr(runtime, "base_dir", "") or "")
                    except Exception:
                        base_dir = None
                result = get_process_executor().run_named(
                    handler,
                    timeout_s=timeout_s,
                    payload={"base_dir": base_dir},
                )
                status = "ok" if result.ok else result.status
            else:
                from api.deps import peek_runtime

                runtime = peek_runtime()
                if runtime is None:
                    time.sleep(0.2)
                    self.bus.publish(TOPIC_L3_TASK, event)
                    return

                bounded = get_non_hang_kernel().run_bounded(
                    lambda: dispatch_warmup_handler(handler, runtime, timeout_s=timeout_s),
                    timeout_s=timeout_s,
                )
                status = "ok" if bounded.ok else bounded.status

            self.bus.publish(
                TOPIC_L3_DONE,
                {"label": label, "handler": handler, "status": status},
            )
        finally:
            with self._lock:
                self._active = max(0, self._active - 1)


_worker: Optional[GovernanceWorkerV3] = None
_worker_lock = threading.Lock()


def get_governance_worker_v3() -> GovernanceWorkerV3:
    global _worker
    with _worker_lock:
        if _worker is None:
            _worker = GovernanceWorkerV3()
        return _worker


def start_governance_worker_v3() -> GovernanceWorkerV3:
    worker = get_governance_worker_v3()
    worker.start()
    return worker
