"""Frozen ExecutionRecord schema (CP-3)."""

from core.kernel.schema.schema_lock import (
    RECORD_SCHEMA_VERSION,
    SchemaViolation,
    load_schema,
    validate_execution_record,
)

__all__ = [
    "RECORD_SCHEMA_VERSION",
    "SchemaViolation",
    "load_schema",
    "validate_execution_record",
]
