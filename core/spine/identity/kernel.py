"""Execution Identity Kernel v1 — hash of normalized execution structure."""

from __future__ import annotations

import hashlib
import json
from typing import Any


IDENTITY_VERSION = "execution-identity-v1"
IDENTITY_PREFIX = "I-"


class ExecutionIdentityKernel:
    """Compute stable execution identity from graph + state + control signatures."""

    def compute(self, execution_bundle: dict[str, Any]) -> str:
        normalized = self._normalize(execution_bundle)
        graph_sig = self._hash_part(normalized["graph"])
        state_sig = self._hash_part(normalized["state"])
        control_sig = self._hash_part(normalized["control"])
        causal_sig = self._hash_part(normalized["causal"])
        digest = hashlib.sha256(f"{graph_sig}|{state_sig}|{control_sig}|{causal_sig}".encode()).hexdigest()
        return f"{IDENTITY_PREFIX}{digest[:16]}"

    def signatures(self, execution_bundle: dict[str, Any]) -> dict[str, str]:
        normalized = self._normalize(execution_bundle)
        return {
            "graph": self._hash_part(normalized["graph"]),
            "state": self._hash_part(normalized["state"]),
            "control": self._hash_part(normalized["control"]),
            "causal": self._hash_part(normalized["causal"]),
        }

    def _normalize(self, bundle: dict[str, Any]) -> dict[str, Any]:
        graph = bundle.get("graph") or {}
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []

        id_to_sig: dict[str, str] = {}
        node_sigs: list[str] = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            eid = str(n.get("event_id") or "")
            sig = f"{n.get('phase') or '?'}:{n.get('event_type') or n.get('event_type') or 'unknown'}"
            if eid:
                id_to_sig[eid] = sig
            node_sigs.append(sig)

        edge_sigs: list[str] = []
        for e in edges:
            if not isinstance(e, dict):
                continue
            frm = str(e.get("from_id") or e.get("from") or "")
            to = str(e.get("to_id") or e.get("to") or "")
            kind = str(e.get("kind") or "executes")
            edge_sigs.append(f"{id_to_sig.get(frm, frm)}>{id_to_sig.get(to, to)}:{kind}")

        state_rows = self._canonical_state(bundle.get("state") or {})
        control_rows = self._canonical_control(bundle.get("control") or [])
        causal_rows = self._canonical_causal(bundle.get("events") or [])

        return {
            "graph": {"nodes": sorted(node_sigs), "edges": sorted(edge_sigs)},
            "state": state_rows,
            "control": control_rows,
            "causal": causal_rows,
        }

    @staticmethod
    def _canonical_state(state: dict[str, Any]) -> list[str]:
        rows: list[str] = []
        for block in (state.get("deltas") or state.get("patches") or []):
            if not isinstance(block, dict):
                continue
            delta = block.get("delta") or block.get("state_delta") or block
            if not isinstance(delta, dict):
                continue
            changes = delta.get("changes") or []
            count = delta.get("change_count")
            keys = sorted(
                str(c.get("field") or c.get("key") or c)
                if isinstance(c, dict)
                else str(c)
                for c in changes
            )
            rows.append(f"changes:{count or len(keys)}:{','.join(keys)}")
        return sorted(rows)

    @staticmethod
    def _canonical_control(control: list[dict[str, Any]]) -> list[str]:
        rows: list[str] = []
        for row in control:
            if not isinstance(row, dict):
                continue
            decision = str(row.get("decision") or "ALLOW")
            entry = str(row.get("entry") or row.get("caller") or "")
            rows.append(f"{entry}:{decision}")
        return sorted(rows)

    @staticmethod
    def _canonical_causal(events: list[dict[str, Any]]) -> list[str]:
        rows: list[str] = []
        for ev in events:
            if not isinstance(ev, dict):
                continue
            etype = str(ev.get("event_type") or ev.get("type") or "")
            for edge in ev.get("causal_edges") or []:
                if not isinstance(edge, dict):
                    continue
                rows.append(
                    f"{etype}:{edge.get('relation')}:{edge.get('from')}->{edge.get('to')}"
                )
        return sorted(rows)

    @staticmethod
    def _hash_part(value: Any) -> str:
        payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:12]
