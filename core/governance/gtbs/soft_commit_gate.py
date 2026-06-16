"""CP-2 — soft commit gate for WriteIntent (provenance + mutability checks)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from core.governance.gtbs.write_intent import MutabilityLevel, WriteIntent


@dataclass(frozen=True)
class SoftGateVerdict:
    allowed: bool
    reason: str = "ok"

    @classmethod
    def ok(cls) -> "SoftGateVerdict":
        return cls(allowed=True)

    @classmethod
    def deny(cls, reason: str) -> "SoftGateVerdict":
        return cls(allowed=False, reason=reason)


class SoftCommitGate:
    """Validate write intents before commit (CP-2 soft enforcement)."""

    @staticmethod
    def validate(intent: WriteIntent) -> SoftGateVerdict:
        prov = intent.provenance
        has_trace = bool(prov.trace_id)
        has_token = bool(prov.runtime_token)

        if intent.mutability is MutabilityLevel.EXPLICIT:
            if not (has_trace or has_token):
                return SoftGateVerdict.deny("explicit write missing trace_id and runtime_token")
            return SoftGateVerdict.ok()

        if intent.mutability is MutabilityLevel.IMPLICIT:
            if not has_token:
                return SoftGateVerdict.deny("implicit write missing runtime_token")
            return SoftGateVerdict.ok()

        if not (has_trace or has_token):
            return SoftGateVerdict.deny("advisory write missing provenance lineage")
        return SoftGateVerdict.ok()

    @staticmethod
    def validate_tuple(intent: WriteIntent) -> Tuple[bool, str]:
        verdict = SoftCommitGate.validate(intent)
        return verdict.allowed, verdict.reason
