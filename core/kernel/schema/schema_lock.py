"""ExecutionRecord schema freeze — CP-3 truth structure lock."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

RECORD_SCHEMA_VERSION = "execution-record-v1"

_FROZEN_KEYS = frozenset(
    {
        "version",
        "trace_id",
        "intent_type",
        "result",
        "identity",
        "graph_invariant",
        "graph",
        "nodes",
        "edges",
        "equivalence",
        "state_projection",
        "causal_projection",
        "explain_projection",
        "replay_signature",
        "audit_log",
        "audit",
        "events",
        "derivation",
        "elapsed_ms",
    }
)


class SchemaViolation(Exception):
    """Raised when ExecutionRecord violates frozen v1 schema."""


def schema_path() -> Path:
    return Path(__file__).resolve().parent / "execution_record_v1.json"


def load_schema() -> dict[str, Any]:
    with schema_path().open(encoding="utf-8") as fh:
        return json.load(fh)


def validate_execution_record(data: dict[str, Any], *, strict: bool = True) -> None:
    """Validate record dict against frozen v1 keys and version."""
    if data.get("version") != RECORD_SCHEMA_VERSION:
        raise SchemaViolation(f"version must be {RECORD_SCHEMA_VERSION!r}")

    unknown = set(data.keys()) - _FROZEN_KEYS
    if unknown and strict:
        raise SchemaViolation(f"unknown record keys: {sorted(unknown)}")

    required = [
        "trace_id",
        "intent_type",
        "result",
        "nodes",
        "edges",
        "state_projection",
        "causal_projection",
        "explain_projection",
        "audit_log",
    ]
    for key in required:
        if key not in data:
            raise SchemaViolation(f"missing required key: {key}")
