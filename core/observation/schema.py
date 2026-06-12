"""Observation Runtime Layer v1 — canonical event schema."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

OBSERVATION_CONTRACT_VERSION = "0.1.0"

# Four laws — North Star (see docs/architecture/CNexus_Runtime_Observation_Boundary_Contract_v0.1.md)
OBSERVATION_NORTH_STAR: tuple[str, ...] = (
    "runtime_emits_events_only",
    "cnexus_reads_and_projects_only",
    "append_only_jsonl_bus",
    "influence_test_proves_no_back_edge",
)

CONTRACT_META: dict[str, Any] = {
    "observational_only": True,
    "no_runtime_mutation": True,
    "no_control_assumption": True,
    "no_reverse_edge": True,
    "contract_version": OBSERVATION_CONTRACT_VERSION,
}

# Keys stripped on ingest — control / execution semantics must not enter the bus
CONTROL_STRIP_KEYS: frozenset[str] = frozenset(
    {
        "action",
        "execute",
        "commit",
        "approve",
        "reject",
        "block",
        "winner",
        "control_signal",
        "adjust_params",
        "target",
        "enforce",
        "mutation_authority",
    }
)


@dataclass
class ObservationEvent:
    timestamp: str
    source: str
    event_type: str
    payload: dict[str, Any]
    schema_version: str = OBSERVATION_CONTRACT_VERSION
    envelope: dict[str, Any] = field(default_factory=lambda: dict(CONTRACT_META))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_parts(cls, *, source: str, event_type: str, payload: dict[str, Any]) -> ObservationEvent:
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source,
            event_type=event_type,
            payload=payload,
        )
