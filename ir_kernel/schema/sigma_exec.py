"""Σ_exec — append-only execution slice (replay artifact)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0.0"


def new_trace_id() -> str:
    return f"tr_{uuid.uuid4().hex[:16]}"


def new_runtime_id() -> str:
    return f"rt_{uuid.uuid4().hex[:16]}"


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class MemoryRef:
    ref_type: str
    ref_id: str
    score: float = 0.0
    excerpt_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_type": self.ref_type,
            "ref_id": self.ref_id,
            "score": self.score,
            "excerpt_hash": self.excerpt_hash,
        }


@dataclass
class CommitEvent:
    """Pending write to Σ_cognitive — executed only via CommitRunner."""

    kind: str
    role: str
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "role": self.role,
            "content": self.content,
            "meta": self.meta,
        }


@dataclass
class ExecStep:
    step_id: str
    step_index: int
    node_id: str
    op: str
    layer: str
    input_keys: List[str]
    output_key: str
    output_preview: str
    output_hash: str
    cost_delta: Dict[str, Any]
    verifier: Dict[str, Any]
    state_variables: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_index": self.step_index,
            "node_id": self.node_id,
            "op": self.op,
            "layer": self.layer,
            "input_keys": self.input_keys,
            "output_key": self.output_key,
            "output_preview": self.output_preview,
            "output_hash": self.output_hash,
            "cost_delta": self.cost_delta,
            "verifier": self.verifier,
            "state_variables": dict(self.state_variables),
        }


@dataclass
class SigmaExec:
    schema_version: str = SCHEMA_VERSION
    trace_id: str = field(default_factory=new_trace_id)
    runtime_id: str = field(default_factory=new_runtime_id)
    graph_id: str = ""
    status: str = "pending"
    input: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    memory_refs: List[MemoryRef] = field(default_factory=list)
    pending_commits: List[CommitEvent] = field(default_factory=list)
    steps: List[ExecStep] = field(default_factory=list)
    cost: Dict[str, Any] = field(default_factory=lambda: {
        "tokens_est": 0,
        "latency_ms": 0,
        "llm_calls": 0,
        "memory_ops": 0,
        "budget": {"max_tokens": 8000, "max_llm_calls": 1},
        "remaining_tokens": 8000,
    })
    error: Optional[Dict[str, Any]] = None
    started_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    def append_step(self, step: ExecStep) -> None:
        self.steps.append(step)
        self.variables.update(step.state_variables)
        self.updated_at = _now_iso()
        delta = step.cost_delta
        self.cost["tokens_est"] = int(self.cost.get("tokens_est", 0)) + int(delta.get("tokens_est", 0))
        self.cost["latency_ms"] = int(self.cost.get("latency_ms", 0)) + int(delta.get("latency_ms", 0))
        if step.op == "CALL_LLM":
            self.cost["llm_calls"] = int(self.cost.get("llm_calls", 0)) + 1
        if step.op == "RETRIEVE":
            self.cost["memory_ops"] = int(self.cost.get("memory_ops", 0)) + 1
        budget = self.cost.get("budget") or {}
        max_tokens = int(budget.get("max_tokens", 8000))
        self.cost["remaining_tokens"] = max(0, max_tokens - int(self.cost["tokens_est"]))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "runtime_id": self.runtime_id,
            "graph_id": self.graph_id,
            "status": self.status,
            "input": self.input,
            "variables": dict(self.variables),
            "memory_refs": [r.to_dict() for r in self.memory_refs],
            "pending_commits": [c.to_dict() for c in self.pending_commits],
            "steps": [s.to_dict() for s in self.steps],
            "cost": dict(self.cost),
            "error": self.error,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SigmaExec":
        sigma = cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            trace_id=data.get("trace_id", new_trace_id()),
            runtime_id=data.get("runtime_id", new_runtime_id()),
            graph_id=data.get("graph_id", ""),
            status=data.get("status", "pending"),
            input=dict(data.get("input") or {}),
            variables=dict(data.get("variables") or {}),
            cost=dict(data.get("cost") or {}),
            error=data.get("error"),
            started_at=data.get("started_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )
        for r in data.get("memory_refs") or []:
            sigma.memory_refs.append(
                MemoryRef(
                    ref_type=r.get("ref_type", "recall_excerpt"),
                    ref_id=r.get("ref_id", ""),
                    score=float(r.get("score", 0)),
                    excerpt_hash=r.get("excerpt_hash", ""),
                )
            )
        for c in data.get("pending_commits") or []:
            sigma.pending_commits.append(
                CommitEvent(
                    kind=c.get("kind", "capture"),
                    role=c.get("role", "user"),
                    content=c.get("content", ""),
                    meta=dict(c.get("meta") or {}),
                )
            )
        return sigma


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
