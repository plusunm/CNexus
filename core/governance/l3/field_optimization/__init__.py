"""L3-G3 — power field optimization layer (stability solver, no execution)."""

from core.governance.l3.field_optimization.attractor_map import AttractorMap
from core.governance.l3.field_optimization.field_builder import PowerFieldBuilder
from core.governance.l3.field_optimization.field_optimizer import (
    FieldOptimizationSimulator,
    FieldOptimizer,
)
from core.governance.l3.field_optimization.l3g3_report import L3G3Report, L3G3Reporter
from core.governance.l3.field_optimization.stability_solver import StabilitySolver
from core.governance.l3.field_optimization.types import (
    OptimizationResult,
    PowerField,
    PowerEdge,
    PowerNode,
    StabilityLandscape,
)

__all__ = [
    "AttractorMap",
    "FieldOptimizationSimulator",
    "FieldOptimizer",
    "L3G3Report",
    "L3G3Reporter",
    "OptimizationResult",
    "PowerField",
    "PowerFieldBuilder",
    "PowerEdge",
    "PowerNode",
    "StabilityLandscape",
    "StabilitySolver",
]
