"""Frozen / experimental CNexus modules — not on production hot path.

Modules listed here remain importable for research tests but must not be
wired into BrainMemoryRuntime.capture / process_interaction without explicit opt-in.

Frozen trees (P0-4):
- core/governance/l7/
- core/governance/l8/
- core/governance/gtbs/          (opt-in via cdg.enable_gtbs_* config only)
- core/governance/semantic_safety/v4-v6/
"""

FROZEN_MODULE_PREFIXES = (
    "core.governance.l7",
    "core.governance.l8",
    "core.governance.gtbs",
    "core.governance.semantic_safety.v4",
    "core.governance.semantic_safety.v5",
    "core.governance.semantic_safety.v6",
)

HOT_PATH_MODULES = (
    "brain_memory.runtime",
    "memory.manager",
    "core.governance.cdg",
    "core.governance.deliberation",
    "core.governance.pipeline",
    "core.governance.values_governance",
)
