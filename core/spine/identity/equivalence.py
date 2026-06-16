"""Replay equivalence — compare execution identity across traces."""

from __future__ import annotations

from typing import Any

from core.spine.identity.bundle import build_execution_bundle
from core.spine.identity.kernel import ExecutionIdentityKernel


class ReplayEquivalence:
    def __init__(self, kernel: ExecutionIdentityKernel | None = None) -> None:
        self.kernel = kernel or ExecutionIdentityKernel()

    def is_equivalent(
        self,
        bundle_a: dict[str, Any],
        bundle_b: dict[str, Any],
    ) -> dict[str, Any]:
        id_a = self.kernel.compute(bundle_a)
        id_b = self.kernel.compute(bundle_b)
        sig_a = self.kernel.signatures(bundle_a)
        sig_b = self.kernel.signatures(bundle_b)
        return {
            "equivalent": id_a == id_b,
            "identity_a": id_a,
            "identity_b": id_b,
            "signature_diff": {
                k: sig_a.get(k) != sig_b.get(k)
                for k in ("graph", "state", "control", "causal")
            },
        }

    def compare_traces(
        self,
        trace_a: str,
        events_a: list[dict[str, Any]],
        trace_b: str,
        events_b: list[dict[str, Any]],
        *,
        control_a: list[dict[str, Any]] | None = None,
        control_b: list[dict[str, Any]] | None = None,
        state_a: dict[str, Any] | None = None,
        state_b: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        bundle_a = build_execution_bundle(trace_a, events_a, control=control_a, state=state_a)
        bundle_b = build_execution_bundle(trace_b, events_b, control=control_b, state=state_b)
        result = self.is_equivalent(bundle_a, bundle_b)
        result["trace_a"] = trace_a
        result["trace_b"] = trace_b
        return result
