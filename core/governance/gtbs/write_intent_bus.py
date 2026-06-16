"""CP-1.5 / CP-2 — WriteIntentBus: shadow emit + soft commit gate."""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import replace
from typing import Any, Dict, Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.spine.writer import SpineWriter

from core.governance.gtbs.exceptions import WriteIntentRejected
from core.governance.gtbs.soft_commit_gate import SoftCommitGate
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.types import AuditTransactionEvent
from core.governance.gtbs.write_intent import (
    GTBS_SOFT_COMMIT_MODE,
    GTBS_WRITE_INTENT_MODE,
    GTBS_WRITE_INTENT_VERSION,
    WriteIntent,
    WriteProvenance,
)
from core.runtime.trace_context import resolve_trace_id
from memory.runtime_guard import current_runtime_token

_provenance_ctx: ContextVar[Optional[WriteProvenance]] = ContextVar(
    "cnexus_write_intent_provenance",
    default=None,
)


def shadow_emit_enabled(*, config: Optional[Dict[str, Any]] = None) -> bool:
    gtbs = (config or {}).get("gtbs") or {}
    if "enable_write_intent_shadow" in gtbs:
        return bool(gtbs["enable_write_intent_shadow"])
    env = os.environ.get("GTBS_WRITE_INTENT_SHADOW", "1").strip().lower()
    return env in ("1", "true", "yes")


def soft_commit_enabled(*, config: Optional[Dict[str, Any]] = None) -> bool:
    gtbs = (config or {}).get("gtbs") or {}
    if "enable_write_intent_soft_gate" in gtbs:
        return bool(gtbs["enable_write_intent_soft_gate"])
    env = os.environ.get("GTBS_WRITE_INTENT_SOFT_GATE", "").strip().lower()
    return env in ("1", "true", "yes")


def build_current_provenance(
    *,
    overrides: Optional[WriteProvenance] = None,
) -> WriteProvenance:
    base = _provenance_ctx.get() or WriteProvenance()
    if overrides is not None:
        base = overrides
    runtime_token = current_runtime_token()
    if runtime_token and base.runtime_token != runtime_token:
        base = replace(base, runtime_token=runtime_token)
    return base


@contextmanager
def write_intent_provenance_scope(
    *,
    trace_id: Optional[str] = None,
    dispatch_kind: Optional[str] = None,
    caller: str = "http",
    channel: str = "brain-memory-ui",
    entry_registry: Optional[str] = None,
) -> Iterator[WriteProvenance]:
    effective_trace = resolve_trace_id(trace_id)
    provenance = WriteProvenance(
        trace_id=effective_trace,
        dispatch_kind=dispatch_kind,
        caller=caller,
        channel=channel,
        entry_registry=entry_registry,
    )
    token: Token = _provenance_ctx.set(provenance)
    try:
        yield build_current_provenance()
    finally:
        _provenance_ctx.reset(token)


class WriteIntentBus:
    """Unified write intent bus — CP-1.5 shadow + CP-2 soft commit gate."""

    GTBS_VERSION = GTBS_WRITE_INTENT_VERSION

    def __init__(
        self,
        transaction_log: GTBSTransactionLog,
        *,
        spine_writer: Optional["SpineWriter"] = None,
        enable_spine_projection: bool = True,
    ) -> None:
        self._log = transaction_log
        self._spine: Optional["SpineWriter"] = spine_writer
        if self._spine is None and enable_spine_projection:
            try:
                from core.spine.writer import SpineWriter
                from core.spine.integration import register_spine_writer

                self._spine = SpineWriter.from_gtbs_log(transaction_log)
                self._spine.hydrate_trace_heads_from_disk()
                register_spine_writer(self._spine)
            except Exception:
                self._spine = None

    def _append_audit(self, event: AuditTransactionEvent) -> None:
        self._log.append(event)
        if self._spine is not None:
            self._spine.project_audit_event(event)

    @property
    def log_path(self):
        return self._log.path

    @property
    def mode(self) -> str:
        return GTBS_SOFT_COMMIT_MODE if soft_commit_enabled() else GTBS_WRITE_INTENT_MODE

    def emit(self, intent: WriteIntent, *, config: Optional[Dict[str, Any]] = None) -> str:
        """Record intent; enforce soft gate when CP-2 is enabled."""
        intent.provenance = build_current_provenance(overrides=intent.provenance)
        if soft_commit_enabled(config=config):
            verdict = SoftCommitGate.validate(intent)
            if not verdict.allowed:
                self._append_rejection(intent, verdict.reason)
                raise WriteIntentRejected(intent.intent_id, verdict.reason)
            return self._append_proposal(intent, shadow=False, mode=GTBS_SOFT_COMMIT_MODE)
        return self._append_proposal(intent, shadow=True, mode=GTBS_WRITE_INTENT_MODE)

    def emit_shadow(self, intent: WriteIntent) -> str:
        """Backward-compatible alias — routes through emit()."""
        return self.emit(intent)

    def _append_proposal(self, intent: WriteIntent, *, shadow: bool, mode: str) -> str:
        payload = intent.to_audit_payload()
        payload["shadow"] = shadow
        payload["gtbs_mode"] = mode
        payload["gtbs_version"] = self.GTBS_VERSION
        self._append_audit(
            AuditTransactionEvent(
                event_type="proposal",
                transaction_id=intent.intent_id,
                payload=payload,
            )
        )
        return intent.intent_id

    def _append_rejection(self, intent: WriteIntent, reason: str) -> None:
        self._append_audit(
            AuditTransactionEvent(
                event_type="rejection",
                transaction_id=intent.intent_id,
                payload={
                    "reason": reason,
                    "write_intent_kind": intent.kind.value,
                    "gtbs_mode": GTBS_SOFT_COMMIT_MODE,
                    "provenance": intent.provenance.to_dict(),
                },
            )
        )

    def record_shadow_commit(
        self,
        intent_id: str,
        *,
        receipt: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Post-execution receipt for write intents."""
        self._append_audit(
            AuditTransactionEvent(
                event_type="commit",
                transaction_id=intent_id,
                payload={
                    "shadow": not soft_commit_enabled(),
                    "gtbs_mode": self.mode,
                    "committed_at": receipt or {},
                },
            )
        )

    def record_rollback(
        self,
        intent_id: str,
        *,
        reason: str,
        tier: str = "A",
    ) -> None:
        self._append_audit(
            AuditTransactionEvent(
                event_type="rejection",
                transaction_id=intent_id,
                payload={
                    "rollback": True,
                    "tier": tier,
                    "reason": reason,
                    "gtbs_mode": GTBS_SOFT_COMMIT_MODE,
                },
            )
        )
