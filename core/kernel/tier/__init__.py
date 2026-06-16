"""Execution tier routing — T0 fast through T3 full truth."""

from core.kernel.tier.resolver import ExecutionTier, resolve_execution_tier
from core.kernel.tier.fast_path import execute_fast_chat
from core.kernel.tier.minimal_path import execute_minimal

__all__ = [
    "ExecutionTier",
    "resolve_execution_tier",
    "execute_fast_chat",
    "execute_minimal",
]
