"""L7 — Post-hoc transition reconstruction from audit projections (Axiom 4).

Multi-store epistemic control system contract:
- Transitions are reconstructed from log pairs, not forward model F(S, u).
- No canonical Σ; operates on audit projection ϕ(S).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TransitionOperator(str, Enum):
    HOLD = "hold"
    INGEST = "ingest"
    PRUNE = "prune"
    CONTROL = "control"
    UNKNOWN = "unknown"


@dataclass
class StateVector:
    """Compact observability state S_t (audit projection)."""

    potential_v: float
    rcs: float
    grounding_avg: float
    d_v: float
    entropy_rate: float

    @classmethod
    def from_record(cls, record: Dict[str, Any]) -> "StateVector":
        return cls(
            potential_v=float(record.get("potential_v") or record.get("v") or 0.0),
            rcs=float(record.get("rcs") or 0.0),
            grounding_avg=float(record.get("grounding_avg") or 0.0),
            d_v=float(record.get("d_v") or 0.0),
            entropy_rate=float(record.get("entropy_rate") or 0.0),
        )

    def norm_sq(self) -> float:
        return (
            self.potential_v ** 2
            + (1.0 - self.rcs) ** 2
            + (1.0 - self.grounding_avg) ** 2
        )


@dataclass
class StateTransition:
    """Explicit transition T: S_t → S_{t+1} with graph delta evidence."""

    index: int
    s_t: Dict[str, Any]
    s_next: Dict[str, Any]
    state_t: StateVector
    state_next: StateVector
    operator: TransitionOperator
    node_delta: int
    edge_delta: int
    parent_edges_delta: int
    hash_changed: bool
    tip_chain_valid: bool
    hash_evolution_valid: bool
    violations: List[str] = field(default_factory=list)

    @property
    def legality_score(self) -> float:
        if self.violations:
            return max(0.0, 1.0 - len(self.violations) / 5.0)
        checks = [
            self.tip_chain_valid,
            self.hash_evolution_valid,
            self.operator != TransitionOperator.UNKNOWN,
        ]
        return sum(1.0 for c in checks if c) / len(checks)


class TransitionReconstructor:
    """Build transition graph from ordered audit records."""

    MAX_NODE_SHRINK = 3

    def build(self, records: List[Dict[str, Any]]) -> List[StateTransition]:
        transitions: List[StateTransition] = []
        for i in range(len(records) - 1):
            s_t = records[i]
            s_next = records[i + 1]
            transitions.append(self._pair(i, s_t, s_next))
        return transitions

    def _pair(self, index: int, s_t: Dict[str, Any], s_next: Dict[str, Any]) -> StateTransition:
        state_t = StateVector.from_record(s_t)
        state_next = StateVector.from_record(s_next)

        n0 = int(s_t.get("graph_nodes") or 0)
        n1 = int(s_next.get("graph_nodes") or 0)
        e0 = int(s_t.get("graph_edges") or 0)
        e1 = int(s_next.get("graph_edges") or 0)
        node_delta = n1 - n0
        edge_delta = e1 - e0

        tip_t = s_t.get("reality_tip")
        tip_n = s_next.get("reality_tip")
        tip_parent = s_next.get("tip_parent_id")

        audit_parent_edges = s_next.get("parent_edges_delta")
        if audit_parent_edges is not None:
            parent_edges_delta = int(audit_parent_edges)
        elif tip_parent and tip_n and edge_delta > 0:
            parent_edges_delta = min(edge_delta, 1)
        else:
            parent_edges_delta = 0

        h0 = s_t.get("graph_hash") or s_t.get("prev_graph_hash")
        h1 = s_next.get("graph_hash")
        hash_changed = bool(h0 and h1 and h0 != h1)

        approved = bool(s_next.get("approved"))

        tip_chain_valid = self._tip_chain_valid(tip_t, tip_n, tip_parent, approved=approved)
        hash_evolution_valid = self._hash_evolution_valid(
            node_delta, edge_delta, hash_changed, h0, h1
        )
        operator = self._classify_operator(s_t, s_next, node_delta, tip_t, tip_n)

        violations: List[str] = []
        if approved and not tip_n:
            violations.append("missing_reality_tip")
        if approved and not h1:
            violations.append("missing_graph_hash")
        if not tip_chain_valid:
            violations.append("tip_chain_break")
        if not hash_evolution_valid:
            violations.append("hash_evolution_mismatch")
        if approved and node_delta < -self.MAX_NODE_SHRINK:
            violations.append("structural_shrink")

        violations.extend(
            self._operator_delta_violations(operator, node_delta, edge_delta, approved=approved)
        )
        violations.extend(
            self._audit_delta_crosscheck(s_next, node_delta, edge_delta)
        )
        if (
            approved
            and operator == TransitionOperator.INGEST
            and node_delta > 0
            and parent_edges_delta < 1
        ):
            violations.append("ingest_missing_parent_edge")

        topology_score = self._topology_reconstruction_score(
            node_delta, edge_delta, parent_edges_delta, tip_chain_valid
        )
        if topology_score < 0.5 and approved:
            violations.append("topology_reconstruction_weak")

        return StateTransition(
            index=index,
            s_t=s_t,
            s_next=s_next,
            state_t=state_t,
            state_next=state_next,
            operator=operator,
            node_delta=node_delta,
            edge_delta=edge_delta,
            parent_edges_delta=parent_edges_delta,
            hash_changed=hash_changed,
            tip_chain_valid=tip_chain_valid,
            hash_evolution_valid=hash_evolution_valid,
            violations=violations,
        )

    @staticmethod
    def _topology_reconstruction_score(
        node_delta: int,
        edge_delta: int,
        parent_edges_delta: int,
        tip_chain_valid: bool,
    ) -> float:
        """Axiom 4 — richer projection diff improves post-hoc reconstruction quality."""
        structure_change = abs(node_delta) + abs(edge_delta) + abs(parent_edges_delta)
        structure_score = 1.0 if structure_change < 50 else 0.65
        return min(1.0, max(0.0, (structure_score + (1.0 if tip_chain_valid else 0.4)) / 2))

    @staticmethod
    def _tip_chain_valid(
        tip_t: Optional[str],
        tip_n: Optional[str],
        tip_parent: Optional[str],
        *,
        approved: bool,
    ) -> bool:
        if not tip_n:
            return False
        if not tip_t:
            return True
        if tip_n == tip_t:
            return True
        if tip_parent and tip_parent == tip_t:
            return True
        if approved and tip_n != tip_t and tip_parent is None:
            return False
        return tip_parent is None

    @staticmethod
    def _operator_delta_violations(
        operator: TransitionOperator,
        node_delta: int,
        edge_delta: int,
        *,
        approved: bool,
    ) -> List[str]:
        if not approved:
            return []
        violations: List[str] = []
        if operator == TransitionOperator.INGEST and node_delta > 0 and edge_delta < 1:
            violations.append("ingest_missing_edge")
        if operator == TransitionOperator.HOLD:
            if node_delta != 0:
                violations.append("hold_node_delta")
            if edge_delta != 0:
                violations.append("hold_edge_delta")
        if operator == TransitionOperator.PRUNE and node_delta >= 0:
            violations.append("prune_without_shrink")
        return violations

    @staticmethod
    def _audit_delta_crosscheck(
        s_next: Dict[str, Any],
        node_delta: int,
        edge_delta: int,
    ) -> List[str]:
        violations: List[str] = []
        audit_node = s_next.get("node_delta")
        audit_edge = s_next.get("edge_delta")
        if audit_node is not None and int(audit_node) != node_delta:
            violations.append("node_delta_mismatch")
        if audit_edge is not None and int(audit_edge) != edge_delta:
            violations.append("edge_delta_mismatch")
        return violations

    @staticmethod
    def _hash_evolution_valid(
        node_delta: int,
        edge_delta: int,
        hash_changed: bool,
        h0: Optional[str],
        h1: Optional[str],
    ) -> bool:
        if not h1:
            return False
        if not h0:
            return True
        if node_delta == 0 and edge_delta == 0:
            return not hash_changed or h0 == h1
        return hash_changed

    @staticmethod
    def _classify_operator(
        s_t: Dict[str, Any],
        s_next: Dict[str, Any],
        node_delta: int,
        tip_t: Optional[str],
        tip_n: Optional[str],
    ) -> TransitionOperator:
        interventions = s_next.get("interventions") or []
        v_jump = abs(
            float(s_next.get("potential_v") or 0) - float(s_t.get("potential_v") or 0)
        )
        if any(
            x in interventions
            for x in ("GRADIENT_DESCENT", "HARD_OVERRIDE_APPLIED", "SOFT_DAMPING")
        ):
            return TransitionOperator.CONTROL
        if node_delta < 0:
            return TransitionOperator.PRUNE
        if tip_n and tip_t and tip_n != tip_t:
            return TransitionOperator.INGEST
        if node_delta > 0:
            return TransitionOperator.INGEST
        if v_jump > 0.05:
            return TransitionOperator.CONTROL
        return TransitionOperator.HOLD
