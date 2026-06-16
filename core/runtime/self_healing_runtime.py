"""CNEXUS Self-Healing Runtime Layer v1 — detect, classify, repair, verify."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from core.runtime.linkage_debug import (
    build_linkage_debug_payload,
    collect_linkage_snapshot,
    resolve_diagnosis,
    resolve_root_cause,
)

RecoveryHandler = Callable[[str], bool]
_SnapshotBuilder = Callable[[], Dict[str, Any]]

_recovery_handler: Optional[RecoveryHandler] = None
_snapshot_builder: Optional[_SnapshotBuilder] = None

_FAULT_TO_ACTIONS: Dict[str, List[str]] = {
    "BOOT_INJECTION_FAILURE": ["reinject_runtime_pointer"],
    "RUNTIME_THREAD_NOT_RUNNING": ["restart_runtime_thread"],
    "RUNTIME_DEAD_AFTER_SPAWN": ["restart_runtime_thread", "reinject_runtime_pointer"],
    "L3_HEARTBEAT_NOT_STARTED": ["start_l3_tick_loop"],
    "L3_DEADLOCK": ["flush_queue", "restart_scheduler"],
    "EVENT_FABRIC_BROKEN": ["rebind_event_bus"],
    "BOOT_IN_PROGRESS": [],
    "RUNTIME_INIT_FAILED": [],
    "RUNTIME_NOT_READY": [],
    "L3_SCHEDULER_OVERLOAD": [],
    "CONTROL_PLANE_FAILURE": [],
    "SYSTEM_HEALTHY": [],
}


def self_healing_enabled() -> bool:
    from core.runtime.control_plane_isolation import self_healing_worker_enabled

    return self_healing_worker_enabled()


def configure_self_healing(
    *,
    recovery_handler: RecoveryHandler,
    snapshot_builder: Optional[_SnapshotBuilder] = None,
) -> None:
    global _recovery_handler, _snapshot_builder
    _recovery_handler = recovery_handler
    _snapshot_builder = snapshot_builder


class FaultClassifier:
    @staticmethod
    def classify(snapshot: Dict[str, Any]) -> str:
        root = resolve_root_cause(snapshot)
        if root == "SYSTEM_HEALTHY":
            return "HEALTHY"
        return root


class RepairPlanner:
    @staticmethod
    def plan(fault: str) -> List[str]:
        if fault == "HEALTHY":
            return []
        return list(_FAULT_TO_ACTIONS.get(fault, []))


class RecoveryExecutor:
    @staticmethod
    def execute(actions: List[str]) -> List[Dict[str, Any]]:
        if not actions or _recovery_handler is None:
            return []
        results: List[Dict[str, Any]] = []
        for action in actions:
            try:
                ok = bool(_recovery_handler(action))
            except Exception as exc:
                ok = False
                results.append({"action": action, "ok": False, "error": exc.__class__.__name__})
                continue
            results.append({"action": action, "ok": ok})
        return results


class StabilityVerifier:
    @staticmethod
    def verify(snapshot: Dict[str, Any], diagnosis: Optional[Dict[str, Any]] = None) -> bool:
        diag = diagnosis or resolve_diagnosis(snapshot)
        if diag.get("root_cause") == "SYSTEM_HEALTHY":
            return True
        runtime = snapshot.get("runtime") or {}
        l3 = snapshot.get("l3") or {}
        event = snapshot.get("event") or {}
        if not runtime.get("pointer"):
            return False
        if diag.get("root_cause") == "L3_HEARTBEAT_NOT_STARTED":
            return l3.get("ticks", 0) > 0
        if diag.get("root_cause") == "EVENT_FABRIC_BROKEN":
            return bool(event.get("flow_active"))
        if diag.get("status") in ("READY", "DEGRADED") and diag.get("root_cause") == "BOOT_IN_PROGRESS":
            return True
        return diag.get("status") == "READY"


class SelfHealingRuntimeLayer:
    def tick(self, snapshot: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if snapshot is None:
            snapshot = _build_snapshot()

        fault = FaultClassifier.classify(snapshot)
        if fault == "HEALTHY":
            return {"result": "OK", "fault": fault, "actions": [], "executed": []}

        actions = RepairPlanner.plan(fault)
        executed = RecoveryExecutor.execute(actions)
        after_snapshot = _build_snapshot()
        after_diagnosis = resolve_diagnosis(after_snapshot)
        healed = StabilityVerifier.verify(after_snapshot, after_diagnosis)
        return {
            "result": "HEALED" if healed else "RETRY_REQUIRED",
            "fault": fault,
            "actions": actions,
            "executed": executed,
            "after": after_diagnosis,
        }


def _build_snapshot() -> Dict[str, Any]:
    if _snapshot_builder is not None:
        return _snapshot_builder()
    return collect_linkage_snapshot()


def run_self_healing_tick() -> Dict[str, Any]:
    if not self_healing_enabled() or _recovery_handler is None:
        return {"result": "DISABLED"}
    return SelfHealingRuntimeLayer().tick()


def build_self_healing_report(*, heal: bool = False) -> Dict[str, Any]:
    payload = build_linkage_debug_payload()
    if not heal or not self_healing_enabled():
        return payload
    healing = SelfHealingRuntimeLayer().tick(
        {
            "control": payload["control"],
            "runtime": payload["runtime"],
            "l3": payload["l3"],
            "cognition": payload["cognition"],
            "event": payload["event"],
            "linkage": payload.get("linkage"),
        }
    )
    payload["healing"] = healing
    refreshed = build_linkage_debug_payload()
    payload.update(
        {
            "control": refreshed["control"],
            "runtime": refreshed["runtime"],
            "l3": refreshed["l3"],
            "cognition": refreshed["cognition"],
            "event": refreshed["event"],
            "diagnosis": refreshed["diagnosis"],
            "status": refreshed["status"],
            "root_cause": refreshed["root_cause"],
            "layer": refreshed["layer"],
            "evidence": refreshed["evidence"],
            "recommended_action": refreshed["recommended_action"],
        }
    )
    return payload
