"""Append-only L3 / boot execution trace for replay diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.runtime import trace_store


def configure_execution_trace(base_dir: str) -> None:
    trace_store.configure_trace_store(base_dir)


def append_execution_trace(base_dir: Optional[str], row: Dict[str, Any]) -> None:
    trace_store.append_trace_row(base_dir, row)


def trace_file_path(base_dir: Optional[str] = None) -> Optional[Path]:
    return trace_store.trace_file_path(base_dir)


def trace_stats(base_dir: Optional[str] = None, *, tail_lines: int = 80) -> Dict[str, Any]:
    """Lightweight event-fabric probe — tail read only, safe for debug endpoint."""
    return trace_store.trace_stats(base_dir, tail_lines=tail_lines)
