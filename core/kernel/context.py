"""Execution context — propagated through kernel → router → runtime."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionContext:
    trace_id: str
    identity_id: Optional[str] = None

    runtime_state: Dict[str, Any] = field(default_factory=dict)
    causal_stack: List[str] = field(default_factory=list)

    start_ts: float = field(default_factory=time.time)
    tags: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def elapsed_ms(self) -> float:
        return (time.time() - self.start_ts) * 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "identity_id": self.identity_id,
            "elapsed_ms": self.elapsed_ms(),
            "tags": self.tags,
            "meta": self.meta,
        }
