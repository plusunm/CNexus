"""
L8 — Unified Collapse & Governance Kernel (convergence layer).

Flattens L3-G0~G7 + Safety V1~V7 into a single semantic tensor field.
NOT a new governance layer — tensor-only observational compression.
"""

from __future__ import annotations

from typing import Any

from core.governance.l8.collapse_unifier import CollapseUnifier
from core.governance.l8.governance_unifier import GovernanceUnifier
from core.governance.l8.l8_report import L8Reporter, build_l8_report
from core.governance.l8.safety_unifier import SafetyUnifier
from core.governance.l8.semantic_tensor_core import SemanticTensorCore
from core.governance.l8.types import (
    L8_CONSTRAINTS,
    L8Report,
    CollapseField,
    GovernanceSurface,
    SafetyEnvelope,
    SemanticTensor,
    UnifiedState,
)
from core.governance.l8.unified_kernel import (
    UnifiedKernel,
    build_l8_unified_state,
    collect_l3_stack,
    collect_observability_streams,
    collect_safety_stack,
)

__all__ = [
    "L8_CONSTRAINTS",
    "L8Report",
    "L8Reporter",
    "CollapseField",
    "CollapseUnifier",
    "GovernanceSurface",
    "GovernanceUnifier",
    "SafetyEnvelope",
    "SafetyUnifier",
    "SemanticTensor",
    "SemanticTensorCore",
    "UnifiedKernel",
    "UnifiedState",
    "build_l8_report",
    "build_l8_unified_state",
    "collect_l3_stack",
    "collect_observability_streams",
    "collect_safety_stack",
]
