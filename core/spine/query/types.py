"""CP-2 Spine Query — request/response contract v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SCHEMA_VERSION = "spine-query-1"

ExplainMode = Literal["causal", "linear", "event", "control", "state", "explain"]


@dataclass
class ParsedQuery:
    trace_id: str
    mode: ExplainMode = "causal"
    limit: int = 200


@dataclass
class SpineQueryResponse:
    trace_id: str
    mode: ExplainMode
    events: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    control: list[dict[str, Any]]
    state: dict[str, Any]
    explanation: dict[str, Any]
    fusion_v2: dict[str, Any] = field(default_factory=dict)
    subgraph: dict[str, Any] = field(default_factory=dict)
    causal: dict[str, Any] = field(default_factory=dict)
    execution: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "mode": self.mode,
            "events": self.events,
            "edges": self.edges,
            "subgraph": self.subgraph,
            "causal": self.causal,
            "execution": self.execution,
            "control": self.control,
            "state": self.state,
            "explanation": self.explanation,
            "fusion_v2": self.fusion_v2,
            "meta": self.meta,
        }
