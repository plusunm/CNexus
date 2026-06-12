"""Semantic Safety v4 — semantic firewall orchestrator."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v4.control_projection_blocker import ControlProjectionBlocker
from core.governance.semantic_safety.v4.governance_phrase_filter import GovernancePhraseFilter
from core.governance.semantic_safety.v4.output_rewriter import OutputRewriter
from core.governance.semantic_safety.v4.risk_interpreter import RiskInterpreter
from core.governance.semantic_safety.v4.safety_tags_injector import SafetyTagsInjector


@dataclass
class FirewallResult:
    output: dict[str, Any]
    firewall_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**self.output, "firewall_status": self.firewall_status}


class SemanticFirewall:
    """
    Pre-output semantic containment firewall.

    Does not mutate runtime, does not govern, does not change stored observational records.
    Produces a presentation-safe view with original payload preserved.
    """

    def __init__(self) -> None:
        self._phrase_filter = GovernancePhraseFilter()
        self._projection_blocker = ControlProjectionBlocker()
        self._risk_interpreter = RiskInterpreter()
        self._rewriter = OutputRewriter()
        self._tag_injector = SafetyTagsInjector()

    def process(self, raw_observability_output: dict[str, Any]) -> FirewallResult:
        original = copy.deepcopy(raw_observability_output)

        blocked_phrases = self._phrase_filter.scan_tree(raw_observability_output)
        projected, projection_count = self._projection_blocker.block(raw_observability_output)
        interpreted = self._risk_interpreter.annotate_tree(projected)
        rewritten = self._rewriter.rewrite(interpreted, observational_payload=original)
        final = self._tag_injector.inject(rewritten)

        status = {
            "blocked_governance_phrases": len(blocked_phrases),
            "governance_phrase_hits": blocked_phrases,
            "control_projections_removed": projection_count,
            "firewall_pass": True,
        }
        return FirewallResult(output=final, firewall_status=status)


def apply_semantic_firewall(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply v4 firewall to a single observational output dict."""
    return SemanticFirewall().process(payload).to_dict()
